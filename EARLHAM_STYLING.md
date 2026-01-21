# Earlham Institute Style Guide Implementation

## Overview
The CellXGene Explorer landing page has been updated to match the Earlham Institute brand identity and style guide.

## Color Palette

### Primary Colors
- **Earlham Red** (`#C61F16`): Primary brand color used for headers, buttons, and interactive elements
- **Dark Red** (`#a01812`): Secondary brand color for depth and gradients
- **Light Red** (`#e8594d`): Lighter accent for hover states and highlights

### Action Colors
- **Primary Red** (`#C61F16`): Used for action buttons (Launch button)
- **Hover Red** (`#8d1510`): Darker red for hover states
- **Success Green** (`#27ae60`): Used for success states and confirmations

### Neutral Colors
- **Background** (`#f5f5f5`): Clean, light neutral background
- **Card Background** (`#ffffff`): Pure white for cards and content areas
- **Text Primary** (`#2d3436`): Dark grey for main text content
- **Text Secondary** (`#636e72`): Medium grey for secondary information
- **Borders** (`#dfe6e9`): Light grey for subtle borders

## Design Elements

### Header
- Linear gradient from Earlham Red to darker red
- Bold 4px bottom border in light red accent color
- Enhanced padding for more prominence
- White text on red background
- Includes Earlham Institute branding in subtitle

### Cards & Components
- **Dataset Cards**: Left border highlight on hover (red)
- **Statistics Cards**: Left border in red, hover elevation effect with color transition
- **Filter Section**: Top border accent in red
- Consistent shadow using brand colors with slight red tint

### Interactive Elements
- **Launch Button**: Bold Earlham red with hover transition to darker red
- **Search Button**: Matching red brand color
- **Hover States**: Subtle elevation and color transitions to darker red
- **Active States**: Clear feedback on interaction
- **Focus States**: Red border on input focus

### Typography & Spacing
- Clean, modern sans-serif font stack
- Increased spacing for better readability
- Clear visual hierarchy with color-coded sections

## Branding Updates

### Page Elements
1. **Page Title**: "CellXGene Explorer | Earlham Institute"
2. **Header Subtitle**: "Earlham Institute | Browse and explore single-cell datasets"
3. **Footer**: Updated to include Earlham Institute copyright and link

### Links
- Earlham Institute website link added to footer
- Links styled in Earlham teal color
- Consistent hover states across all links

## Visual Enhancements

### Shadows & Depth
- Custom shadows with red tint (`rgba(198, 31, 22, 0.1)`)
- Enhanced shadows on hover for better interactivity feedback
- Stronger shadow on header for visual hierarchy

### Loading Spinner
- Updated to use Earlham brand colors
- Red gradient animation for consistency

### Consistency
- All interactive elements follow the same color scheme
- Consistent border radius (8px for cards, 4px for buttons)
- Uniform spacing and padding throughout

## Accessibility

All color combinations maintain:
- WCAG AA contrast ratios
- Clear visual hierarchy
- Readable text on all backgrounds
- Distinct interactive states

## Files Modified

1. **styles.css**: Complete color scheme and styling overhaul
2. **index.html**: Branding updates in title, header, and footer

## Preview

To see the changes:
```bash
docker-compose build landing-page
docker-compose up -d landing-page
```

Then visit: http://localhost (or your configured port)

## Color Reference Card

```
Primary Red:      #C61F16  ████████
Dark Red:         #a01812  ████████
Light Red:        #e8594d  ████████
Hover Red:        #8d1510  ████████
Success Green:    #27ae60  ████████
Background:       #f5f5f5  ████████
Text Dark:        #2d3436  ████████
Text Light:       #636e72  ████████
Border:           #dfe6e9  ████████
```

## Consistency with Earlham Brand

This implementation reflects the Earlham Institute's commitment to:
- **Scientific Excellence**: Clean, professional design with bold brand presence
- **Innovation**: Modern, interactive UI with clear visual hierarchy
- **Accessibility**: Strong contrast between red headers and white text, readable content
- **Brand Recognition**: Consistent use of the iconic Earlham red (#C61F16) throughout the interface
