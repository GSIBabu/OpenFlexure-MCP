# OpenFlexure-MCP
MCP server for the OpenFlexure Microscope

The repo hosts the MCP server for interfacing with the Openflexure Python client.

Requirements:
------------------------------------
You need to have the OFM sitting on the same Wi-Fi network as your device runnning Claude Desktop. 

You need to know the IP address of the OFM, to manually pass it to Claude in case it can't find it on your network.

What tools do you have available?
------------------------------------
The OpenFlexure MCP server provides the following tools:
* move_stage - Moves the microscope stage to specific X, Y, Z coordinates (absolute or relative)
* capture_image - Captures an image (high quality or quick preview)
* autofocus - Runs the autofocus routine to find optimal focus
* call_extension - Calls specific extension methods on the microscope
* run_z_stack - Captures a series of images at different Z positions (focus depths)
  
Additionally, these resources are available:

* microscope://info - Information about the connected microscope
* microscope://position - Current stage position
* microscope://extensions - Available microscope extensions

The server also includes template prompts for common operations like capturing images at specific positions, creating Z-stacks, and exploring extensions.

