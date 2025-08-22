"""
Upload utilities for cloud services
"""

import os
import aiohttp
import asyncio
from typing import Optional
from bot.config import Config

async def upload_to_gofile(file_path: str) -> Optional[str]:
    """
    Upload file to GoFile.io
    """
    try:
        # First, get a server
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.gofile.io/getServer') as response:
                if response.status == 200:
                    data = await response.json()
                    if data['status'] == 'ok':
                        server = data['data']['server']
                    else:
                        return None
                else:
                    return None
        
        # Upload file to the server
        upload_url = f'https://{server}.gofile.io/uploadFile'
        
        async with aiohttp.ClientSession() as session:
            with open(file_path, 'rb') as file:
                data = aiohttp.FormData()
                data.add_field('file', file, filename=os.path.basename(file_path))
                
                if Config.GOFILE_TOKEN:
                    data.add_field('token', Config.GOFILE_TOKEN)
                
                async with session.post(upload_url, data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result['status'] == 'ok':
                            return result['data']['downloadPage']
        
        return None
    
    except Exception as e:
        print(f"Error uploading to GoFile: {e}")
        return None

async def upload_to_streamtape(file_path: str) -> Optional[str]:
    """
    Upload file to Streamtape
    """
    try:
        if not Config.STREAMTAPE_API_USERNAME or not Config.STREAMTAPE_API_PASS:
            return None
        
        # Get upload server
        async with aiohttp.ClientSession() as session:
            upload_url = f'https://api.streamtape.com/file/ul?login={Config.STREAMTAPE_API_USERNAME}&key={Config.STREAMTAPE_API_PASS}'
            
            async with session.get(upload_url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data['status'] == 200:
                        upload_url = data['result']['url']
                    else:
                        return None
                else:
                    return None
        
        # Upload file
        async with aiohttp.ClientSession() as session:
            with open(file_path, 'rb') as file:
                data = aiohttp.FormData()
                data.add_field('file1', file, filename=os.path.basename(file_path))
                
                async with session.post(upload_url, data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result['status'] == 200:
                            return result['result']['url']
        
        return None
    
    except Exception as e:
        print(f"Error uploading to Streamtape: {e}")
        return None

async def upload_large_file(file_path: str) -> Optional[str]:
    """
    Upload large file to appropriate cloud service
    """
    # Try GoFile first
    gofile_link = await upload_to_gofile(file_path)
    if gofile_link:
        return gofile_link
    
    # Try Streamtape as fallback
    streamtape_link = await upload_to_streamtape(file_path)
    if streamtape_link:
        return streamtape_link
    
    return None

async def delete_from_gofile(file_id: str, account_token: str) -> bool:
    """
    Delete file from GoFile (requires premium account)
    """
    try:
        if not account_token:
            return False
        
        async with aiohttp.ClientSession() as session:
            delete_url = f'https://api.gofile.io/deleteContent'
            data = {
                'contentId': file_id,
                'token': account_token
            }
            
            async with session.delete(delete_url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['status'] == 'ok'
        
        return False
    
    except Exception as e:
        print(f"Error deleting from GoFile: {e}")
        return False
