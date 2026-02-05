"""
Private Access API Routes

Provides REST API for private dataset access management.

Constitutional Alignment:
- Principle IV (Fail-Fast): Clear error responses
- Principle VI (Accessibility): User-friendly error messages
"""

from flask import Blueprint, jsonify, request, current_app, session, redirect
from datetime import datetime
import logging
from functools import wraps

from ..models.access_grant import AccessGrant, AccessGrantStore, generate_access_code
from ..models.shareable_link import ShareableLink, ShareableLinkStore, generate_share_token
from ..errors import format_error_response

private_bp = Blueprint("private", __name__)
logger = logging.getLogger(__name__)


def get_grant_store() -> AccessGrantStore:
    """Get the access grant store from app config."""
    return current_app.config["GRANT_STORE"]


def get_link_store() -> ShareableLinkStore:
    """Get the shareable link store from app config."""
    return current_app.config["LINK_STORE"]


def get_private_catalog():
    """Get the private catalog from app config."""
    return current_app.config.get("PRIVATE_CATALOG")


def require_verified_access(f):
    """Decorator to require verified email or share link access for a dataset."""
    @wraps(f)
    def decorated_function(dataset_id, *args, **kwargs):
        # Check session for verified email or share link access
        verified_email = session.get('verified_email')
        share_link_access = session.get('share_link_access', False)
        verified_datasets = session.get('verified_datasets', [])
        
        # Must have either email verification OR share link access
        if not verified_email and not share_link_access:
            return jsonify({
                "error": "Authentication required",
                "message": "Please verify your email to access this dataset",
                "error_type": "AuthenticationRequired"
            }), 401
        
        # Check if this dataset is in the user's verified datasets
        if dataset_id not in verified_datasets:
            return jsonify({
                "error": "Access denied",
                "message": "You do not have access to this dataset",
                "error_type": "AccessDenied"
            }), 403
        
        # Log access (only if email-based, share links track their own usage)
        if verified_email:
            store = get_grant_store()
            grant = store.get_by_email_and_dataset(verified_email, dataset_id)
            if grant:
                grant.log_access()
                store.save(grant)
        
        return f(dataset_id, *args, **kwargs)
    
    return decorated_function


@private_bp.route("/request-access", methods=["POST"])
def request_access():
    """
    Request access to a private dataset.
    
    This is called by reviewers who have been told to access a private dataset.
    It sends an access code to their email.
    
    Request body:
        - email: Reviewer's email address
        - dataset_id: ID of the private dataset
        
    Returns:
        JSON response confirming code was sent
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body required"}), 400
        
        email = data.get("email", "").strip().lower()
        dataset_id = data.get("dataset_id", "").strip()
        
        if not email or "@" not in email:
            return jsonify({"error": "Valid email address required"}), 400
        
        if not dataset_id:
            return jsonify({"error": "Dataset ID required"}), 400
        
        # Check if dataset exists in private catalog
        private_catalog = get_private_catalog()
        if not private_catalog:
            return jsonify({"error": "Private datasets not configured"}), 500
        
        try:
            dataset = private_catalog.get_by_id(dataset_id)
        except Exception:
            return jsonify({"error": "Dataset not found"}), 404
        
        store = get_grant_store()
        
        # Check for existing valid grant
        existing_grant = store.get_by_email_and_dataset(email, dataset_id)
        
        if existing_grant and not existing_grant.revoked:
            # Re-send code for existing grant (generate new code)
            access_code = generate_access_code()
            existing_grant.code_hash = existing_grant.__class__.__bases__  # Will update
            
            # Actually create new grant to replace (simpler than updating hash)
            access_code = generate_access_code()
            new_grant = AccessGrant.create(
                dataset_id=dataset_id,
                email=email,
                access_code=access_code,
                expires_in_days=90
            )
            # Preserve ID and access log
            new_grant.id = existing_grant.id
            new_grant.access_log = existing_grant.access_log
            store.save(new_grant)
            grant = new_grant
        else:
            # Create new grant
            access_code = generate_access_code()
            grant = AccessGrant.create(
                dataset_id=dataset_id,
                email=email,
                access_code=access_code,
                expires_in_days=90
            )
            store.save(grant)
        
        # Send email with access code
        email_service = current_app.config.get("EMAIL_SERVICE")
        if email_service:
            email_service.send_access_code(
                to_email=email,
                access_code=access_code,
                dataset_name=dataset.display_name,
                expires_at=grant.expires_at
            )
            logger.info(f"Access code sent to {email} for dataset {dataset_id}")
        else:
            # For development: log the code
            logger.warning(f"EMAIL SERVICE NOT CONFIGURED - Access code for {email}: {access_code}")
        
        return jsonify({
            "success": True,
            "message": f"Access code sent to {email}",
            "expires_at": grant.expires_at
        }), 200
        
    except Exception as e:
        logger.error(f"Error requesting access: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to process request"}), 500


@private_bp.route("/verify", methods=["POST"])
def verify_access():
    """
    Verify an access code.
    
    Request body:
        - email: Reviewer's email address
        - code: The access code from their email
        
    Returns:
        JSON response with verification result
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body required"}), 400
        
        email = data.get("email", "").strip().lower()
        code = data.get("code", "").strip()
        
        if not email or not code:
            return jsonify({"error": "Email and code required"}), 400
        
        store = get_grant_store()
        
        # Find grant by email and code
        grant = store.get_by_email_and_code(email, code)
        
        if not grant:
            return jsonify({
                "error": "Invalid code",
                "message": "The email or code you entered is incorrect"
            }), 401
        
        # Mark as verified
        grant.verified = True
        grant.verified_at = datetime.utcnow().isoformat()
        store.save(grant)
        
        # Get all grants for this email to set up session
        all_grants = store.get_all_grants_for_email(email)
        verified_datasets = [g.dataset_id for g in all_grants]
        
        # Set session
        session['verified_email'] = email
        session['verified_datasets'] = verified_datasets
        
        logger.info(f"Access verified for {email} - {len(verified_datasets)} dataset(s) accessible")
        
        return jsonify({
            "success": True,
            "message": "Access verified",
            "email": email,
            "datasets_accessible": len(verified_datasets)
        }), 200
            
    except Exception as e:
        logger.error(f"Error verifying access: {str(e)}", exc_info=True)
        return jsonify({"error": "Verification failed"}), 500


@private_bp.route("/session", methods=["GET"])
def get_session():
    """
    Get current session info.
    
    Returns:
        JSON with verified email and accessible datasets
    """
    verified_email = session.get('verified_email')
    verified_datasets = session.get('verified_datasets', [])
    share_link_access = session.get('share_link_access', False)
    
    # User is authenticated if they have a verified email OR share link access
    is_authenticated = verified_email is not None or (share_link_access and len(verified_datasets) > 0)
    
    return jsonify({
        "authenticated": is_authenticated,
        "email": verified_email or ("Share Link Access" if share_link_access else None),
        "accessible_datasets": verified_datasets,
        "share_link_access": share_link_access
    }), 200


@private_bp.route("/logout", methods=["POST"])
def logout():
    """Clear session."""
    session.clear()
    return jsonify({"success": True, "message": "Logged out"}), 200


@private_bp.route("/datasets", methods=["GET"])
def list_private_datasets():
    """
    List private datasets accessible to the current session.
    
    Returns:
        JSON with list of accessible private datasets
    """
    verified_email = session.get('verified_email')
    verified_datasets = session.get('verified_datasets', [])
    share_link_access = session.get('share_link_access', False)
    
    # If no email verification and no share link access, return empty
    if not verified_email and not (share_link_access and verified_datasets):
        return jsonify({
            "datasets": [],
            "message": "Not authenticated"
        }), 200
    
    private_catalog = get_private_catalog()
    if not private_catalog:
        return jsonify({"datasets": [], "count": 0}), 200
    
    datasets = []
    accessible_dataset_ids = set()
    
    # Add datasets from email grants
    if verified_email:
        store = get_grant_store()
        grants = store.get_grants_for_email(verified_email)
        for grant in grants:
            accessible_dataset_ids.add(grant.dataset_id)
    
    # Add datasets from share link access
    if share_link_access and verified_datasets:
        for dataset_id in verified_datasets:
            accessible_dataset_ids.add(dataset_id)
    
    # Fetch dataset details
    for dataset_id in accessible_dataset_ids:
        try:
            dataset = private_catalog.get_by_id(dataset_id)
            datasets.append(dataset.to_dict())
        except Exception:
            # Dataset may have been removed
            continue
    
    return jsonify({
        "datasets": datasets,
        "count": len(datasets),
        "email": verified_email or ("Share Link Access" if share_link_access else None)
    }), 200


@private_bp.route("/datasets/<dataset_id>", methods=["GET"])
@require_verified_access
def get_private_dataset(dataset_id: str):
    """
    Get details for a private dataset.
    
    Requires verified access.
    """
    private_catalog = get_private_catalog()
    
    try:
        dataset = private_catalog.get_by_id(dataset_id)
        return jsonify(dataset.to_dict()), 200
    except Exception as e:
        return jsonify({"error": "Dataset not found"}), 404


@private_bp.route("/datasets/<dataset_id>/launch", methods=["POST"])
@require_verified_access
def launch_private_dataset(dataset_id: str):
    """
    Launch a private dataset in CellXGene.
    
    Requires verified access.
    """
    private_catalog = get_private_catalog()
    container_manager = current_app.config.get("PRIVATE_CONTAINER_MANAGER")
    
    if not container_manager:
        return jsonify({"error": "Private container manager not configured"}), 500
    
    try:
        dataset = private_catalog.get_by_id(dataset_id)
        
        # Launch container using launch_dataset method
        port = container_manager.launch_dataset(dataset_id, dataset.filename)
        # URL format matches nginx config: /cellxgene-{dataset_id}/
        cellxgene_url = f"/cellxgene-{dataset_id}/"
        
        return jsonify({
            "dataset_id": dataset_id,
            "cellxgene_url": cellxgene_url,
            "status": "launching"
        }), 200
        
    except Exception as e:
        logger.error(f"Error launching private dataset: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to launch dataset"}), 500


# Admin endpoints (should be protected in production)
@private_bp.route("/admin/grant", methods=["POST"])
def admin_grant_access():
    """
    Admin endpoint to grant access to a private dataset.
    
    Request body:
        - email: Reviewer's email address
        - dataset_id: ID of the private dataset
        - expires_in_days: Optional, default 90
        
    Returns:
        JSON with grant details and access code
    """
    # TODO: Add admin authentication in production
    admin_token = request.headers.get("X-Admin-Token")
    expected_token = current_app.config.get("ADMIN_TOKEN")
    
    if expected_token and admin_token != expected_token:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        data = request.get_json()
        
        email = data.get("email", "").strip().lower()
        dataset_id = data.get("dataset_id", "").strip()
        expires_in_days = data.get("expires_in_days", 90)
        
        if not email or "@" not in email:
            return jsonify({"error": "Valid email address required"}), 400
        
        if not dataset_id:
            return jsonify({"error": "Dataset ID required"}), 400
        
        # Verify dataset exists
        private_catalog = get_private_catalog()
        if private_catalog:
            try:
                dataset = private_catalog.get_by_id(dataset_id)
                dataset_name = dataset.display_name
            except Exception:
                return jsonify({"error": "Dataset not found"}), 404
        else:
            dataset_name = dataset_id
        
        # Check for existing grant
        store = get_grant_store()
        existing_grant = store.get_by_email_and_dataset(email, dataset_id)
        
        if existing_grant and not existing_grant.revoked and not existing_grant.is_expired():
            return jsonify({
                "error": "Grant already exists",
                "message": f"Access has already been granted to {email} for this dataset",
                "grant_id": existing_grant.id,
                "expires_at": existing_grant.expires_at
            }), 409
        
        # Create grant
        access_code = generate_access_code()
        grant = AccessGrant.create(
            dataset_id=dataset_id,
            email=email,
            access_code=access_code,
            expires_in_days=expires_in_days
        )
        
        store.save(grant)
        
        # Send email
        email_service = current_app.config.get("EMAIL_SERVICE")
        if email_service:
            email_service.send_access_code(
                to_email=email,
                access_code=access_code,
                dataset_name=dataset_name,
                expires_at=grant.expires_at
            )
        
        logger.info(f"Admin granted access to {email} for dataset {dataset_id}")
        
        return jsonify({
            "success": True,
            "grant_id": grant.id,
            "email": email,
            "dataset_id": dataset_id,
            "expires_at": grant.expires_at,
            "access_code": access_code  # Only shown to admin
        }), 201
        
    except Exception as e:
        logger.error(f"Error granting access: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to grant access"}), 500


@private_bp.route("/admin/grants/<dataset_id>", methods=["GET"])
def admin_list_grants(dataset_id: str):
    """
    Admin endpoint to list all grants for a dataset.
    """
    admin_token = request.headers.get("X-Admin-Token")
    expected_token = current_app.config.get("ADMIN_TOKEN")
    
    if expected_token and admin_token != expected_token:
        return jsonify({"error": "Unauthorized"}), 401
    
    store = get_grant_store()
    grants = store.get_grants_for_dataset(dataset_id)
    
    return jsonify({
        "dataset_id": dataset_id,
        "grants": [
            {
                "id": g.id,
                "email": g.email,
                "verified": g.verified,
                "revoked": g.revoked,
                "expired": g.is_expired(),
                "created_at": g.created_at,
                "expires_at": g.expires_at,
                "access_count": len(g.access_log)
            }
            for g in grants
        ],
        "count": len(grants)
    }), 200


@private_bp.route("/admin/revoke/<grant_id>", methods=["POST"])
def admin_revoke_grant(grant_id: str):
    """
    Admin endpoint to revoke a grant.
    """
    admin_token = request.headers.get("X-Admin-Token")
    expected_token = current_app.config.get("ADMIN_TOKEN")
    
    if expected_token and admin_token != expected_token:
        return jsonify({"error": "Unauthorized"}), 401
    
    store = get_grant_store()
    
    if store.revoke(grant_id):
        logger.info(f"Admin revoked grant {grant_id}")
        return jsonify({"success": True, "message": "Grant revoked"}), 200
    else:
        return jsonify({"error": "Grant not found"}), 404


@private_bp.route("/admin/auth-required", methods=["GET"])
def admin_auth_required():
    """
    Check if admin authentication is required.
    
    Returns whether an admin token is configured.
    """
    expected_token = current_app.config.get("ADMIN_TOKEN")
    return jsonify({
        "auth_required": bool(expected_token)
    }), 200


@private_bp.route("/admin/private-datasets", methods=["GET"])
def admin_list_private_datasets():
    """
    Admin endpoint to list all private datasets.
    """
    admin_token = request.headers.get("X-Admin-Token")
    expected_token = current_app.config.get("ADMIN_TOKEN")
    
    if expected_token and admin_token != expected_token:
        return jsonify({"error": "Unauthorized"}), 401
    
    private_catalog = get_private_catalog()
    
    if not private_catalog:
        return jsonify({"datasets": [], "count": 0}), 200
    
    datasets = [ds.to_dict() for ds in private_catalog.get_all()]
    
    return jsonify({
        "datasets": datasets,
        "count": len(datasets)
    }), 200


# ============================================================================
# Shareable Link Endpoints
# ============================================================================

@private_bp.route("/share/<token>", methods=["GET"])
def access_shared_link(token: str):
    """
    Access a private dataset via a shareable link.
    
    This provides one-click access - the user is immediately granted
    access to the dataset and redirected to the viewer launch page.
    
    Args:
        token: The share token from the URL
        
    Returns:
        Redirect to dataset viewer or error page
    """
    try:
        store = get_link_store()
        link = store.get_by_token(token)
        
        if not link:
            logger.warning(f"Invalid or expired share link accessed")
            return jsonify({
                "error": "Invalid or expired link",
                "message": "This share link is invalid, has expired, or has reached its usage limit."
            }), 404
        
        # Record usage
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        user_agent = request.headers.get('User-Agent', '')[:200]  # Truncate for storage
        link.record_use(ip_address=ip_address, user_agent=user_agent)
        store.save(link)
        
        # Set up session for this dataset
        if 'verified_datasets' not in session:
            session['verified_datasets'] = []
        
        if link.dataset_id not in session['verified_datasets']:
            session['verified_datasets'].append(link.dataset_id)
        
        # Mark session as share-link authenticated
        session['share_link_access'] = True
        session['share_link_id'] = link.id
        
        logger.info(f"Share link {link.id} used for dataset {link.dataset_id} (use #{link.use_count})")
        
        # Redirect to the private access page (session is already set up)
        base_url = current_app.config.get("BASE_URL", "")
        return redirect(f"{base_url}/private")
        
    except Exception as e:
        logger.error(f"Error accessing share link: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to access shared link"}), 500


@private_bp.route("/share/<token>/info", methods=["GET"])
def get_shared_link_info(token: str):
    """
    Get information about a shareable link without using it.
    
    This allows the frontend to show link details before the user clicks through.
    """
    try:
        store = get_link_store()
        link = store.get_by_token(token)
        
        if not link:
            return jsonify({
                "valid": False,
                "error": "Invalid or expired link"
            }), 404
        
        # Get dataset info
        private_catalog = get_private_catalog()
        dataset_info = None
        
        if private_catalog:
            try:
                dataset = private_catalog.get_by_id(link.dataset_id)
                dataset_info = {
                    "id": dataset.id,
                    "display_name": dataset.display_name,
                    "description": dataset.description,
                    "organism": dataset.organism,
                    "tissue": dataset.tissue
                }
            except Exception:
                pass
        
        return jsonify({
            "valid": True,
            "link_id": link.id,
            "dataset_id": link.dataset_id,
            "dataset": dataset_info,
            "label": link.label,
            "expires_at": link.expires_at,
            "remaining_uses": (link.max_uses - link.use_count) if link.max_uses else None
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting share link info: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to get link info"}), 500


@private_bp.route("/share/<token>/launch", methods=["POST"])
def launch_via_share_link(token: str):
    """
    Launch a CellXGene container for a dataset accessed via share link.
    
    This is the API endpoint called after the user clicks through the share link.
    """
    try:
        store = get_link_store()
        link = store.get_by_token(token)
        
        if not link:
            return jsonify({
                "error": "Invalid or expired link",
                "message": "This share link is invalid, has expired, or has reached its usage limit."
            }), 404
        
        # Record usage if not already recorded in this session
        if session.get('share_link_id') != link.id:
            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
            user_agent = request.headers.get('User-Agent', '')[:200]
            link.record_use(ip_address=ip_address, user_agent=user_agent)
            store.save(link)
        
        # Get dataset
        private_catalog = get_private_catalog()
        container_manager = current_app.config.get("PRIVATE_CONTAINER_MANAGER")
        
        if not private_catalog:
            return jsonify({"error": "Private datasets not configured"}), 500
        
        if not container_manager:
            return jsonify({"error": "Container manager not configured"}), 500
        
        try:
            dataset = private_catalog.get_by_id(link.dataset_id)
        except Exception:
            return jsonify({"error": "Dataset not found"}), 404
        
        # Launch container
        port = container_manager.launch_dataset(link.dataset_id, dataset.filename)
        cellxgene_url = f"/cellxgene-{link.dataset_id}/"
        
        logger.info(f"Launched container for share link {link.id}, dataset {link.dataset_id}")
        
        return jsonify({
            "dataset_id": link.dataset_id,
            "cellxgene_url": cellxgene_url,
            "status": "launching"
        }), 200
        
    except Exception as e:
        logger.error(f"Error launching via share link: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to launch dataset"}), 500


# ============================================================================
# Admin Shareable Link Endpoints
# ============================================================================

@private_bp.route("/admin/share-links", methods=["POST"])
def admin_create_share_link():
    """
    Admin endpoint to create a shareable link for a private dataset.
    
    Request body:
        - dataset_id: ID of the private dataset
        - created_by_email: Email of the person creating the link
        - label: Optional descriptive label (e.g., "For Nature reviewers")
        - expires_in_days: Optional, default 30
        - max_uses: Optional, maximum number of uses (None = unlimited)
        - send_email: Optional, if true sends the link via email
        - recipient_email: Required if send_email is true
        
    Returns:
        JSON with link details including the full shareable URL
    """
    admin_token = request.headers.get("X-Admin-Token")
    expected_token = current_app.config.get("ADMIN_TOKEN")
    
    if expected_token and admin_token != expected_token:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        data = request.get_json()
        
        dataset_id = data.get("dataset_id", "").strip()
        created_by_email = (data.get("created_by_email") or "").strip().lower()
        label = (data.get("label") or "").strip() or None
        expires_in_days = data.get("expires_in_days", 30)
        max_uses = data.get("max_uses")  # None = unlimited
        send_email = data.get("send_email", False)
        recipient_email = (data.get("recipient_email") or "").strip().lower()
        
        if not dataset_id:
            return jsonify({"error": "Dataset ID required"}), 400
        
        if not created_by_email or "@" not in created_by_email:
            return jsonify({"error": "Valid creator email required"}), 400
        
        if send_email and (not recipient_email or "@" not in recipient_email):
            return jsonify({"error": "Valid recipient email required when send_email is true"}), 400
        
        # Verify dataset exists
        private_catalog = get_private_catalog()
        if private_catalog:
            try:
                dataset = private_catalog.get_by_id(dataset_id)
                dataset_name = dataset.display_name
            except Exception:
                return jsonify({"error": "Dataset not found"}), 404
        else:
            dataset_name = dataset_id
        
        # Generate token and create link
        token = generate_share_token()
        link = ShareableLink.create(
            dataset_id=dataset_id,
            token=token,
            created_by_email=created_by_email,
            label=label,
            expires_in_days=expires_in_days,
            max_uses=max_uses
        )
        
        store = get_link_store()
        store.save(link)
        
        # Build the shareable URL
        base_url = current_app.config.get("BASE_URL", "http://localhost")
        share_url = f"{base_url}/api/private/share/{token}"
        
        # Optionally send email
        if send_email and recipient_email:
            email_service = current_app.config.get("EMAIL_SERVICE")
            if email_service:
                email_service.send_share_link(
                    to_email=recipient_email,
                    share_url=share_url,
                    dataset_name=dataset_name,
                    expires_at=link.expires_at,
                    created_by=created_by_email,
                    label=label
                )
                logger.info(f"Share link sent to {recipient_email} for dataset {dataset_id}")
        
        logger.info(f"Share link created by {created_by_email} for dataset {dataset_id}")
        
        return jsonify({
            "success": True,
            "link_id": link.id,
            "share_url": share_url,
            "token": token,  # Only shown at creation time
            "dataset_id": dataset_id,
            "dataset_name": dataset_name,
            "label": label,
            "expires_at": link.expires_at,
            "max_uses": max_uses,
            "email_sent": send_email and bool(recipient_email)
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating share link: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to create share link"}), 500


@private_bp.route("/admin/share-links/<dataset_id>", methods=["GET"])
def admin_list_share_links(dataset_id: str):
    """
    Admin endpoint to list all share links for a dataset.
    """
    admin_token = request.headers.get("X-Admin-Token")
    expected_token = current_app.config.get("ADMIN_TOKEN")
    
    if expected_token and admin_token != expected_token:
        return jsonify({"error": "Unauthorized"}), 401
    
    store = get_link_store()
    links = store.get_links_for_dataset(dataset_id)
    
    return jsonify({
        "dataset_id": dataset_id,
        "links": [link.to_public_dict() for link in links],
        "count": len(links)
    }), 200


@private_bp.route("/admin/share-links/<link_id>/revoke", methods=["POST"])
def admin_revoke_share_link(link_id: str):
    """
    Admin endpoint to revoke a share link.
    """
    admin_token = request.headers.get("X-Admin-Token")
    expected_token = current_app.config.get("ADMIN_TOKEN")
    
    if expected_token and admin_token != expected_token:
        return jsonify({"error": "Unauthorized"}), 401
    
    store = get_link_store()
    
    if store.revoke(link_id):
        logger.info(f"Admin revoked share link {link_id}")
        return jsonify({"success": True, "message": "Share link revoked"}), 200
    else:
        return jsonify({"error": "Share link not found"}), 404


@private_bp.route("/admin/share-links/stats", methods=["GET"])
def admin_share_link_stats():
    """
    Admin endpoint to get share link statistics.
    """
    admin_token = request.headers.get("X-Admin-Token")
    expected_token = current_app.config.get("ADMIN_TOKEN")
    
    if expected_token and admin_token != expected_token:
        return jsonify({"error": "Unauthorized"}), 401
    
    store = get_link_store()
    stats = store.get_stats()
    
    return jsonify(stats), 200
