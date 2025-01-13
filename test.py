import asyncio
import keyboard

# Define an asynchronous function
async def async_function():
    print("Async function started!")
    await asyncio.sleep(2)  # Simulate a delay
    print("Async function finished!")

# Function to handle key press event
def on_key_event(e):
    print("here")
    asyncio.run(async_function())  # Run async function when 'a' key is pressed

# Listen for the 'a' key press and run the async function
keyboard.on_press(on_key_event)

# Wait for the user to press 'esc' to stop the program
keyboard.wait('esc')
