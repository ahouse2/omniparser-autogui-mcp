#coding: utf-8

import os
import sys
import threading
import io
import asyncio
import tempfile
from contextlib import redirect_stdout
import argparse
import base64
import pyautogui
import pyperclip
from mcp.server.fastmcp import Image
import PIL
import pygetwindow as gw

omniparser_path = os.path.join(os.path.dirname(__file__), '..', '..', 'OmniParser')
sys.path = [omniparser_path, ] + sys.path
from util.omniparser import Omniparser
sys.path = sys.path[1:]

INPUT_IMAGE_SIZE = 960
PADDING_SIZE = 0

def mcp_autogui_main(mcp):
    global omniparser
    input_image_path = ''
    output_dir_path = ''
    omniparser_thread = None
    result_image = None
    input_image_resized_path = None
    detail = None
    is_finished = False

    current_mouse_x, current_mouse_y = pyautogui.position()
    current_window = gw.getActiveWindow()
    with redirect_stdout(sys.stderr):
        def parse_arguments():
            parser = argparse.ArgumentParser(description='Omniparser API')
            parser.add_argument('--som_model_path', type=str, default=os.path.join(omniparser_path, 'weights/icon_detect/model.pt'), help='Path to the som model')
            parser.add_argument('--caption_model_name', type=str, default='florence2', help='Name of the caption model')
            parser.add_argument('--caption_model_path', type=str, default=os.path.join(omniparser_path, 'weights/icon_caption_florence'), help='Path to the caption model')
            parser.add_argument('--device', type=str, default='cuda', help='Device to run the model')
            parser.add_argument('--BOX_TRESHOLD', type=float, default=0.05, help='Threshold for box detection')
            args = parser.parse_args()
            return args
        args = parse_arguments()
        config = vars(args)
        omniparser = Omniparser(config)
        
    temp_dir = tempfile.TemporaryDirectory()
    dname = temp_dir.name

    @mcp.tool()
    async def omniparser_details_on_screen() -> list:
        """Get the screen and analyze its details.
If a timeout occurs, you can continue by running it again.

Return value:
    - Details such as the content of text.
    - Screen capture with ID number added.
"""
        nonlocal omniparser_thread, result_image, detail, is_finished
        detail_text = ''
        with redirect_stdout(sys.stderr):
            def omniparser_thread_func():
                nonlocal result_image, detail, is_finished, detail_text
                with redirect_stdout(sys.stderr):
                    screenshot_image = pyautogui.screenshot()

                    dino_labled_img, detail = omniparser.parse_raw(screenshot_image)

                    image_bytes = base64.b64decode(dino_labled_img)
                    result_image_local = PIL.Image.open(io.BytesIO(image_bytes))

                    width, height = result_image_local.size
                    if width > height:
                        result_image_local = result_image_local.resize((INPUT_IMAGE_SIZE, INPUT_IMAGE_SIZE * height // width))
                    else:
                        result_image_local = result_image_local.resize((INPUT_IMAGE_SIZE * width // height, INPUT_IMAGE_SIZE))

                    result_image = io.BytesIO()
                    result_image_local.save(result_image, format='png')

                    detail_text = ''
                    for loop, content in enumerate(detail):
                        detail_text += f'ID: {loop}, {content['type']}: {content['content']}\n'

                    is_finished = True
            if omniparser_thread is None:
                result_image = None
                detail = None
                is_finished = False
                omniparser_thread = threading.Thread(target=omniparser_thread_func)
                omniparser_thread.start()
            
            while not is_finished:
                await asyncio.sleep(0.1)

            omniparser_thread = None

            return [detail_text, Image(data=result_image.getvalue(), format="png")]

    @mcp.tool()
    async def omniparser_click(id: int, button: str = 'left', clicks: int = 1) -> bool:
        """Click on anything on the screen.

Args:
    id: The element on the screen that it click. You can check it with "omniparser_details_on_screen".
    button: Button to click. 'left', 'middle', or 'right'.
    clicks: Number of clicks. 2 for double click.
Return value:
    True is success. False is means "this is not found".
"""
        nonlocal current_mouse_x, current_mouse_y, current_window
        screen_width, screen_height = pyautogui.size()
        for compos in detail['compos']:
            if compos['id'] == id:
                current_mouse_x = int((compos['position']['column_min'] + compos['position']['column_max']) * (screen_width + PADDING_SIZE * 2) / detail['img_shape'][1] / 2) - PADDING_SIZE
                current_mouse_y = int((compos['position']['row_min'] + compos['position']['row_max']) * (screen_height + PADDING_SIZE * 2) / detail['img_shape'][0] / 2) - PADDING_SIZE
                pyautogui.click(x=current_mouse_x, y=current_mouse_y, button=button, clicks=clicks)
                current_window = gw.getActiveWindow()
                return True
        return False

    @mcp.tool()
    async def omniparser_drags(from_id: int, to_id: int, button: str = 'left', key: str = '') -> bool:
        """Drag and drop on the screen.

Args:
    from_id: The element on the screen that it start to drag. You can check it with "omniparser_details_on_screen".
    to_id: The element on the screen that it end to drag. You can check it with "omniparser_details_on_screen".
    button: Button to click. 'left', 'middle', or 'right'.
    key: The name of the keyboard key if you hold down it while dragging. You can check key's name with "omniparser_get_keys_list".
Return value:
    True is success. False is means "this is not found".
"""
        nonlocal current_mouse_x, current_mouse_y, current_window
        screen_width, screen_height = pyautogui.size()
        from_x = -1
        to_x = -1
        for compos in detail['compos']:
            if compos['id'] == from_id:
                from_x = int((compos['position']['column_min'] + compos['position']['column_max']) * (screen_width + PADDING_SIZE * 2) / detail['img_shape'][1] / 2) - PADDING_SIZE
                from_y = int((compos['position']['row_min'] + compos['position']['row_max']) * (screen_height + PADDING_SIZE * 2) / detail['img_shape'][0] / 2) - PADDING_SIZE
            if compos['id'] == to_id:
                to_x = int((compos['position']['column_min'] + compos['position']['column_max']) * (screen_width + PADDING_SIZE * 2) / detail['img_shape'][1] / 2) - PADDING_SIZE
                to_y = int((compos['position']['row_min'] + compos['position']['row_max']) * (screen_height + PADDING_SIZE * 2) / detail['img_shape'][0] / 2) - PADDING_SIZE
        if from_x == -1 or to_x == -1:
            return False
        if key is not None and key != '':
            pyautogui.keyDown(key)
        pyautogui.moveTo(from_x, from_y)
        pyautogui.dragTo(to_x, to_y, button=button)
        if key is not None and key != '':
            pyautogui.keyUp(key)
        current_mouse_x = to_x
        current_mouse_y = to_y
        current_window = gw.getActiveWindow()
        return True

    @mcp.tool()
    async def omniparser_mouse_move(id: int) -> bool:
        """Moves the mouse cursor over the specified element.

Args:
    id: The element on the screen that it move. You can check it with "omniparser_details_on_screen".
Return value:
    True is success. False is means "this is not found".
"""
        nonlocal current_mouse_x, current_mouse_y, current_window
        screen_width, screen_height = pyautogui.size()
        for compos in detail['compos']:
            if compos['id'] == id:
                current_mouse_x = int((compos['position']['column_min'] + compos['position']['column_max']) * (screen_width + PADDING_SIZE * 2) / detail['img_shape'][1] / 2) - PADDING_SIZE
                current_mouse_y = int((compos['position']['row_min'] + compos['position']['row_max']) * (screen_height + PADDING_SIZE * 2) / detail['img_shape'][0] / 2) - PADDING_SIZE
                pyautogui.moveTo(current_mouse_x, current_mouse_y)
                current_window = gw.getActiveWindow()
                return True
        return False

    @mcp.tool()
    async def omniparser_scroll(clicks: int) -> None:
        """The mouse scrolling wheel behavior.

Args:
    clicks: Amount of scrolling. 10 is scroll up 10 "clicks" and -10 is scroll down 10 "clicks".
"""
        current_window.activate()
        pyautogui.moveTo(current_mouse_x, current_mouse_y)
        pyautogui.scroll(clicks)

    @mcp.tool()
    async def omniparser_write(content: str, id: int = -1) -> None:
        """Type the characters in the string that is passed.

Args:
    content: What to enter.
    id: Click on the target before typing. You can check it with "omniparser_details_on_screen".
"""
        if id >= 0:
            await autogui_click(id)
        else:
            current_window.activate()
            pyautogui.moveTo(current_mouse_x, current_mouse_y)
        if content.isascii():
            pyautogui.write(content)
        else:
            pyperclip.copy(content)
            pyautogui.hotkey('ctrl', 'v')

    @mcp.tool()
    async def omniparser_get_keys_list() -> list[str]:
        """List of keyboard keys. Used in "omniparser_input_key" etc.

Return value:
    List of keyboard keys.
"""
        return pyautogui.KEYBOARD_KEYS

    @mcp.tool()
    async def omniparser_input_key(key1: str, key2: str = '', key3: str = '') -> None:
        """Press of keyboard keys. 

Args:
    key1-3: Press of keyboard keys. You can check key's name with "omniparser_get_keys_list". If you specify multiple, keys will be pressed down in order, and then released in reverse order.
"""
        current_window.activate()
        pyautogui.moveTo(current_mouse_x, current_mouse_y)
        if key2 is not None and key2 != '' and key3 is not None and key3 != '':
            pyautogui.hotkey(key1, key2, key3)
        elif key2 is not None and key2 != '':
            pyautogui.hotkey(key1, key2)
        else:
            pyautogui.hotkey(key1)