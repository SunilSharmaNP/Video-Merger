"""
Upload utility functions for cloud services
"""

import aiohttp
import os
from bot.config import Config

async def upload_large_file(file_path: str) -> str:
    """Upload large file to cloud service"""
    # Try GoFile first
    if Config.GOFILE_TOKEN:
        result = await upload_to_gofile(file_path)
        if result:
            return result
    
    # Try other services or return None
    return await upload_to_gofile_anonymous(file_path)

async def upload_to_gofile(file_path: str) -> str:
    """Upload file to GoFile.io with token"""
    try:
        async with aiohttp.ClientSession() as session:
            # Get upload server
            async with session.get('https://api.gofile.io/getServer') as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                server = data['data']['server']
            
            # Upload file
            with open(file_path, 'rb') as file:
                form_data = aiohttp.FormData()
                form_data.add_field('file', file, filename=os.path.basename(file_path))
                form_data.add_field('token', Config.GOFILE_TOKEN)
                
                async with session.post(f'https://{server}.gofile.io/uploadFile', data=form_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result['status'] == 'ok':
                            return result['data']['downloadPage']
        
        return None
    
    except Exception as e:
        print(f"GoFile upload error: {e}")
        return None

async def upload_to_gofile_anonymous(file_path: str) -> str:
    """Upload file to GoFile.io anonymously"""
    try:
        async with aiohttp.ClientSession() as session:
            # Get upload server
            async with session.get('https://api.gofile.io/getServer') as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                server = data['data']['server']
            
            # Upload file
            with open(file_path, 'rb') as file:
                form_data = aiohttp.FormData()
                form_data.add_field('file', file, filename=os.path.basename(file_path))
                
                async with session.post(f'https://{server}.gofile.io/uploadFile', data=form_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result['status'] == 'ok':
                            return result['data']['downloadPage']
        
        return None
    
    except Exception as e:
        print(f"GoFile anonymous upload error: {e}")
        return None

async def upload_to_streamtape(file_path: str) -> str:
    """Upload file to Streamtape"""
    try:
        if not Config.STREAMTAPE_API_USERNAME or not Config.STREAMTAPE_API_PASS:
            return None
        
        async with aiohttp.ClientSession() as session:
            # Get upload URL
            params = {
                'login': Config.STREAMTAPE_API_USERNAME,
                'key': Config.STREAMTAPE_API_PASS
            }
            
            async with session.get('https://api.streamtape.com/file/ul', params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data['status'] == 200:
                        upload_url = data['result']['url']
                        
                        # Upload file
                        with open(file_path, 'rb') as file:
                            form_data = aiohttp.FormData()
                            form_data.add_field('file1', file, filename=os.path.basename(file_path))
                            
                            async with session.post(upload_url, data=form_data) as upload_response:
                                if upload_response.status == 200:
                                    result = await upload_response.json()
                                    if result['status'] == 200:
                                        return result['result']['url']
        
        return None
    
    except Exception as e:
        print(f"Streamtape upload error: {e}")
        return None
