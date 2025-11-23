# Textual Themes Guide

Textual provides a powerful theming system that allows you to customize the appearance of your terminal applications. This guide covers how to use built-in themes, create custom themes, and integrate them with your CSS.

## Overview

Textual's theme system is built on a comprehensive color management infrastructure:

- **Color Class**: Represents colors in various formats (RGB with alpha, ANSI indices, automatic contrast-based colors)
- **ColorSystem Class**: Generates ~100+ color variables from a set of base colors
- **Theme Class**: Organizes and applies color schemes, providing both built-in and custom themes

## Built-in Themes

Textual includes several pre-configured themes you can use:

- `textual-dark` - Default dark theme with blue accent
- `textual-light` - Light theme variant
- `nord` - Arctic-inspired theme with cool blues
- `gruvbox` - Retro groove theme with warm colors
- `catppuccin-mocha` - Pastel theme with pink primary color
- `tokyo-night` - Dark theme inspired by Tokyo

### Using Built-in Themes

You can apply a built-in theme in two ways:

**Method 1: Class attribute**
```python
from textual.app import App
from textual.theme import Theme

class MyApp(App):
    CSS_PATH = "css/app.tcss"
    theme = Theme("nord")  # Apply theme at class level
    
    def compose(self):
        # Your widgets here
        pass
```

**Method 2: In `on_mount()`**
```python
from textual.app import App
from textual.theme import Theme

class MyApp(App):
    CSS_PATH = "css/app.tcss"
    
    def on_mount(self):
        self.theme = Theme("nord")  # Apply theme dynamically
```

## Creating Custom Themes

To create a custom theme, you'll need to:

1. Define base colors
2. Generate a color system (optional, for automatic palette generation)
3. Create a Theme instance
4. Optionally override specific variables

### Basic Custom Theme

```python
from textual.app import App
from textual.theme import Theme

class MyApp(App):
    CSS_PATH = "css/app.tcss"
    
    def on_mount(self):
        custom_theme = Theme(
            name="custom",
            base_colors={
                "primary": "#3498db",      # Blue
                "secondary": "#2ecc71",    # Green
                "background": "#1e1e1e",   # Dark gray
                "foreground": "#ecf0f1",   # Light gray
                "accent": "#e74c3c",       # Red accent
                "warning": "#f39c12",      # Orange
                "error": "#e74c3c",        # Red
                "success": "#2ecc71",      # Green
            },
            variables={
                # Override specific variables if needed
                "button.background": "#2980b9",
                "button.foreground": "#ffffff",
            }
        )
        self.theme = custom_theme
```

### Advanced Custom Theme with ColorSystem

For more control, you can use `ColorSystem` to generate a full palette:

```python
from textual.app import App
from textual.color import Color
from textual.design import ColorSystem
from textual.theme import Theme

class MyApp(App):
    CSS_PATH = "css/app.tcss"
    
    def on_mount(self):
        # Define base colors
        base_colors = {
            "primary": Color.parse("#3498db"),
            "secondary": Color.parse("#2ecc71"),
            "background": Color.parse("#1e1e1e"),
            "foreground": Color.parse("#ecf0f1"),
        }
        
        # Generate color system
        color_system = ColorSystem(base_colors)
        
        # Create theme from color system
        custom_theme = Theme(color_system)
        
        # Optionally override specific variables
        custom_theme.set_variable("button.background", "#2980b9")
        custom_theme.set_variable("button.foreground", "#ffffff")
        
        self.theme = custom_theme
```

## Using Theme Variables in CSS

Textual themes automatically populate CSS variables that you can use in your `.tcss` files. The syntax uses `$variable-name`:

### Common Theme Variables

Textual provides many built-in variables. Here are some commonly used ones:

- `$primary` - Primary brand color
- `$secondary` - Secondary brand color
- `$accent` - Accent color
- `$background` - Background color
- `$foreground` - Foreground/text color
- `$surface` - Surface color (for containers, panels)
- `$surface-lighten-1`, `$surface-lighten-2`, etc. - Lighter variants
- `$surface-darken-1`, `$surface-darken-2`, etc. - Darker variants
- `$warning` - Warning color
- `$error` - Error color
- `$success` - Success color

### CSS Examples

```css
/* Using theme variables */
Button {
    background: $primary;
    color: $foreground;
}

Container {
    background: $surface;
    border: solid $accent;
}

.user-container {
    background: $surface-lighten-1;
    color: $foreground;
}

.assistant-container {
    background: $surface-lighten-2;
    color: $foreground;
}

.message-text {
    background: $primary;
    color: $foreground;
}

/* Error states */
.error-message {
    background: $error;
    color: $foreground;
}

/* Warning states */
.warning-message {
    background: $warning;
    color: $foreground;
}
```

## Dynamic Theme Switching

You can switch themes at runtime:

```python
from textual.app import App
from textual.theme import Theme

class MyApp(App):
    CSS_PATH = "css/app.tcss"
    
    def on_mount(self):
        self.theme = Theme("textual-dark")
    
    def action_toggle_theme(self):
        """Toggle between dark and light themes"""
        if self.theme.name == "textual-dark":
            self.theme = Theme("textual-light")
        else:
            self.theme = Theme("textual-dark")
        # Theme changes are automatically applied
```

## Best Practices

1. **Use theme variables in CSS**: Instead of hardcoding colors, use `$variable-name` to ensure consistency and easy theme switching.

2. **Define base colors thoughtfully**: Choose base colors that work well together and provide good contrast for accessibility.

3. **Leverage color system variants**: Use `$surface-lighten-1`, `$surface-darken-2`, etc. for subtle variations rather than defining new colors.

4. **Test with different themes**: Ensure your application looks good with both light and dark themes if you plan to support theme switching.

5. **Document custom variables**: If you create custom theme variables, document them so other developers know what's available.

## Example: Complete Theme Integration

Here's a complete example showing theme usage in an app:

```python
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Button, Static
from textual.theme import Theme

class ThemedApp(App):
    CSS_PATH = "css/themed_app.tcss"
    theme = Theme("nord")  # Start with nord theme
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static("Welcome to Themed App", id="title"),
            Button("Click me", id="action-button"),
            id="main-container"
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        # Switch to a different theme
        self.theme = Theme("gruvbox")
```

With corresponding CSS (`css/themed_app.tcss`):

```css
Screen {
    background: $background;
}

#main-container {
    background: $surface;
    border: solid $accent;
    padding: 1;
}

#title {
    color: $foreground;
    text-style: bold;
}

#action-button {
    background: $primary;
    color: $foreground;
}

#action-button:hover {
    background: $primary-lighten-1;
}
```

## Resources

- [Textual Color System Documentation](https://textual.textualize.io/guide/design/)
- [Textual CSS Guide](https://textual.textualize.io/guide/styles/)
- [Textual API Reference - Theme](https://textual.textualize.io/api/theme/)

