from mcp.server.fastmcp import FastMCP, Context, Image
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Optional, Dict, Any, Union, List
import numpy as np
import io
from PIL import Image as PILImage

# Import OpenFlexure client library
import openflexure_microscope_client as ofm_client

@dataclass
class MicroscopeContext:
    microscope: ofm_client.MicroscopeClient

@asynccontextmanager
async def microscope_lifespan(server: FastMCP) -> AsyncIterator[MicroscopeContext]:
    """Connect to the microscope on startup and disconnect on shutdown"""
    # Connect to microscope using the provided IP address
    microscope = ofm_client.MicroscopeClient("192.168.100.124")
    try:
        yield MicroscopeContext(microscope=microscope)
    finally:
        # Clean up connection if needed
        pass  # The client doesn't have an explicit close method based on the README

# Create MCP server with microscope lifespan
mcp = FastMCP(
    "OpenFlexure Microscope", 
    lifespan=microscope_lifespan,
    dependencies=["openflexure-microscope-client", "matplotlib", "numpy", "pillow"]
)

# ---- Resource Endpoints ----

@mcp.resource("microscope://info")
def get_microscope_info() -> str:
    """Get information about the connected microscope"""
    # Access the microscope via the context's request_context
    microscope = mcp.current_context.request_context.lifespan_context.microscope
    
    # Get basic information from the microscope
    # Note: Using the extensions to get device info based on README
    try:
        device_info = microscope.extensions.get("org.openflexure.microscope").get("device-info").get()
        return f"""
        OpenFlexure Microscope Information:
        
        Device ID: {device_info.get('device_id', 'Unknown')}
        Name: {device_info.get('name', 'Unknown')}
        Version: {device_info.get('version', 'Unknown')}
        Board: {device_info.get('board', 'Unknown')}
        
        Active Extensions:
        {', '.join(microscope.extensions.keys())}
        """
    except Exception as e:
        # Fallback if extension not available
        return f"""
        OpenFlexure Microscope connected at: 192.168.100.124
        
        Active Extensions:
        {', '.join(microscope.extensions.keys())}
        
        Error getting detailed info: {str(e)}
        """

@mcp.resource("microscope://position")
def get_position() -> str:
    """Get the current position of the microscope stage"""
    microscope = mcp.current_context.request_context.lifespan_context.microscope
    
    # Get position using the position property mentioned in README
    position = microscope.position
    position_array = microscope.get_position_array()
    
    return f"""
    Current Stage Position:
    
    Dictionary format:
    X: {position.get('x', 0)} steps
    Y: {position.get('y', 0)} steps
    Z: {position.get('z', 0)} steps
    
    Array format: {position_array}
    """

@mcp.resource("microscope://extensions")
def get_extensions() -> str:
    """Get the list of available extensions on the microscope"""
    microscope = mcp.current_context.request_context.lifespan_context.microscope
    
    extensions = microscope.extensions.keys()
    extension_info = []
    
    for ext_name in extensions:
        ext = microscope.extensions[ext_name]
        links = list(ext.keys())
        extension_info.append(f"- {ext_name}: {', '.join(links)}")
    
    return f"""
    Available Microscope Extensions:
    
    {''.join(extension_info)}
    """

# ---- Tool Endpoints ----

@mcp.tool()
def move_stage(ctx: Context, x: Optional[int] = None, y: Optional[int] = None, z: Optional[int] = None, 
               relative: bool = False) -> str:
    """
    Move the microscope stage to a specific position
    
    Parameters:
    - x: X-axis position in steps (optional)
    - y: Y-axis position in steps (optional)
    - z: Z-axis position in steps (optional)
    - relative: If True, perform a relative move; otherwise, absolute move (default: False)
    """
    microscope = ctx.request_context.lifespan_context.microscope
    
    # Create position dictionary with only specified axes
    position = {}
    if x is not None:
        position['x'] = x
    if y is not None:
        position['y'] = y
    if z is not None:
        position['z'] = z
    
    if not position:
        return "No position specified. Please provide x, y, or z coordinates."
    
    # Move the stage using the appropriate method from README
    before_pos = microscope.position.copy()
    
    if relative:
        microscope.move_rel(position)
    else:
        microscope.move(position)
    
    after_pos = microscope.position
    
    return f"""
    Stage moved successfully!
    
    Before: {before_pos}
    After: {after_pos}
    Delta: X: {after_pos['x'] - before_pos['x']}, Y: {after_pos['y'] - before_pos['y']}, Z: {after_pos['z'] - before_pos['z']}
    """

@mcp.tool()
def capture_image(ctx: Context, high_quality: bool = True) -> Image:
    """
    Capture an image from the microscope
    
    Parameters:
    - high_quality: If True, use capture_image(); if False, use grab_image() (default: True)
    """
    microscope = ctx.request_context.lifespan_context.microscope
    
    # Capture image using the appropriate method
    if high_quality:
        ctx.info("Capturing high-quality image...")
        pil_image = microscope.capture_image()
        title = "High-quality image"
    else:
        ctx.info("Grabbing quick preview image...")
        pil_image = microscope.grab_image()
        title = "Preview image"
    
    # Convert PIL image to bytes
    img_byte_arr = io.BytesIO()
    pil_image.save(img_byte_arr, format='PNG')
    img_bytes = img_byte_arr.getvalue()
    
    # Create MCP Image object
    return Image(data=img_bytes, format="png")

@mcp.tool()
def autofocus(ctx: Context) -> str:
    """
    Run the autofocus routine
    """
    microscope = ctx.request_context.lifespan_context.microscope
    
    # Get position before autofocus
    before_z = microscope.position['z']
    
    # Run autofocus as mentioned in README
    ctx.info("Running autofocus routine...")
    result = microscope.autofocus()
    
    # Get position after autofocus
    after_z = microscope.position['z']
    
    return f"""
    Autofocus completed!
    
    Z position before: {before_z}
    Z position after: {after_z}
    Z change: {after_z - before_z}
    
    Autofocus result details:
    {result}
    """

@mcp.tool()
def call_extension(ctx: Context, extension_name: str, link_name: str, 
                 method: str = "get", payload: Optional[Dict[str, Any]] = None) -> str:
    """
    Call a specific extension method on the microscope
    
    Parameters:
    - extension_name: Name of the extension (e.g., "org.openflexure.microscope")
    - link_name: Name of the link within the extension (e.g., "device-info")
    - method: HTTP method to use ("get" or "post") (default: "get")
    - payload: JSON payload for POST requests (optional)
    """
    microscope = ctx.request_context.lifespan_context.microscope
    
    # Check if extension exists
    if extension_name not in microscope.extensions:
        return f"Extension '{extension_name}' not found. Available extensions: {list(microscope.extensions.keys())}"
    
    # Check if link exists
    if link_name not in microscope.extensions[extension_name]:
        return f"Link '{link_name}' not found in extension '{extension_name}'. Available links: {list(microscope.extensions[extension_name].keys())}"
    
    # Call the appropriate method
    try:
        if method.lower() == "get":
            result = microscope.extensions[extension_name][link_name].get()
        elif method.lower() == "post":
            if payload is None:
                payload = {}
            result = microscope.extensions[extension_name][link_name].post_json(payload)
        else:
            return f"Unknown method '{method}'. Please use 'get' or 'post'."
        
        return f"""
        Extension call successful:
        
        Extension: {extension_name}
        Link: {link_name}
        Method: {method}
        
        Result:
        {result}
        """
    except Exception as e:
        return f"Error calling extension: {str(e)}"

@mcp.tool()
def run_z_stack(ctx: Context, start_z: int, end_z: int, steps: int = 10) -> str:
    """
    Run a Z-stack acquisition
    
    Parameters:
    - start_z: Starting Z position
    - end_z: Ending Z position
    - steps: Number of images to capture (default: 10)
    """
    microscope = ctx.request_context.lifespan_context.microscope
    
    # Calculate step size
    z_step = (end_z - start_z) / (steps - 1) if steps > 1 else 0
    
    # Save starting position to return to later
    start_pos = microscope.position.copy()
    
    # Move to starting Z position
    new_pos = start_pos.copy()
    new_pos['z'] = start_z
    microscope.move(new_pos)
    
    # Capture Z-stack
    captured_positions = []
    
    ctx.info(f"Starting Z-stack acquisition from Z={start_z} to Z={end_z} with {steps} steps")
    
    for i in range(steps):
        # Calculate current Z position
        current_z = start_z + i * z_step
        
        # Move to current Z position
        current_pos = new_pos.copy()
        current_pos['z'] = int(current_z)
        microscope.move(current_pos)
        
        # Capture image
        actual_pos = microscope.position
        ctx.info(f"Capturing image {i+1}/{steps} at Z={actual_pos['z']}")
        image = microscope.grab_image()
        
        captured_positions.append({
            'index': i+1,
            'z': actual_pos['z'],
            'image_size': (image.width, image.height)
        })
    
    # Return to starting position
    microscope.move(start_pos)
    
    return f"""
    Z-stack acquisition completed!
    
    Captured {len(captured_positions)} images
    Z range: {start_z} to {end_z}
    Step size: {z_step:.2f}
    
    Images captured at Z positions:
    {[pos['z'] for pos in captured_positions]}
    
    Current position: {microscope.position}
    """

# ---- Prompts ----

@mcp.prompt()
def capture_image_at_position() -> str:
    """Template for capturing an image at a specific position"""
    return """
    I'll help you capture an image at a specific position.
    
    1. First, I'll move the stage to the desired position (X, Y, Z coordinates)
    2. Then I'll capture an image
    3. Finally, I'll return the captured image
    
    Please specify the coordinates where you want to capture the image.
    """

@mcp.prompt()
def z_stack() -> str:
    """Template for capturing a Z-stack of images"""
    return """
    I'll help you capture a Z-stack of images at different focal planes.
    
    Please provide:
    1. Starting Z position
    2. Ending Z position
    3. Number of images to capture in the stack
    
    I'll move the stage to each Z position and capture images at regular intervals.
    """

@mcp.prompt()
def explore_extensions() -> str:
    """Template for exploring microscope extensions"""
    return """
    I'll help you explore the extensions available on your OpenFlexure Microscope.
    
    First, I'll list all the available extensions and their links.
    Then, you can choose a specific extension and link to interact with.
    
    Let me know if you want to call a specific extension function or just explore what's available.
    """

if __name__ == "__main__":
    mcp.run()
