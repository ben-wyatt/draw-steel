I really like Textual.

The layout should start simple: just a chatbot

# Basics


following: https://textual.textualize.io/guide/app/

## Apps

See `from_scratch.py` for example code
Event (triggers) are prefixed with "on_"
events can act as async event handlers (Coroutines)
use async def on_mount(self) and run async functions within
apps run until self.exit(). arguments to exit are returned by app.run()
App[] in class definition type-hint the return of app.run()
"with app.suspend()" suspends app while in context manager
CSS_PATH variable reads css files from disk

## Widgets

self-contained UI elements
compose should return iterable of widgets (use yield)
use self.mount to  trigger a specific widget to be mount
widget mounts trigger async coroutine to render widget, so 

