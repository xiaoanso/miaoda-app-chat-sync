#!/usr/bin/env python3
"""
Streaming Output Generator

Provides streaming/chunked JSON output for large repositories to avoid memory issues.
"""

import json
from typing import Dict, Iterator, Optional, Callable

from core.constants import DEFAULT_CHUNK_SIZE


class StreamingJSONEncoder:
    """
    Streaming JSON encoder for large outputs.
    
    Supports:
    - Chunked output for large file lists
    - Memory-efficient processing
    - Progress callbacks
    """
    
    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE):
        self.chunk_size = chunk_size
    
    def stream_json_chunks(self, data: Dict) -> Iterator[Dict]:
        """
        Generate JSON data in chunks.
        
        Yields:
            Dict chunks with metadata about chunk position
        """
        files = data.get('files', [])
        total_files = len(files)
        
        if total_files == 0:
            yield {'type': 'complete', 'data': data}
            return
        
        # Yield header without files
        header = {k: v for k, v in data.items() if k != 'files'}
        header['files'] = []
        header['chunk_info'] = {
            'total_chunks': (total_files + self.chunk_size - 1) // self.chunk_size,
            'total_files': total_files,
            'current_chunk': 0,
            'chunk_size': self.chunk_size
        }
        
        yield {
            'type': 'header',
            'data': header,
            'chunk_info': header['chunk_info']
        }
        
        # Yield file chunks
        for i in range(0, total_files, self.chunk_size):
            chunk_files = files[i:i + self.chunk_size]
            chunk_data = {
                'type': 'chunk',
                'chunk_index': i // self.chunk_size,
                'files': chunk_files,
                'chunk_info': {
                    'total_chunks': header['chunk_info']['total_chunks'],
                    'total_files': total_files,
                    'current_chunk': i // self.chunk_size + 1,
                    'files_in_chunk': len(chunk_files),
                    'start_index': i,
                    'end_index': min(i + self.chunk_size, total_files)
                }
            }
            yield chunk_data
        
        # Yield completion marker
        yield {
            'type': 'complete',
            'chunk_info': header['chunk_info']
        }
    
    def estimate_size(self, data: Dict) -> int:
        """Estimate total JSON size in bytes."""
        json_str = json.dumps(data, ensure_ascii=False)
        return len(json_str.encode('utf-8'))


class StreamingFileWriter:
    """
    Stream large JSON output to file in chunks.
    
    Features:
    - Write incrementally to avoid memory issues
    - Support for multiple output formats
    - Progress tracking
    """
    
    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE):
        self.chunk_size = chunk_size
        self.encoder = StreamingJSONEncoder(chunk_size=chunk_size)
    
    def write_streaming(self, data: Dict, output_path: str, 
                        progress_callback: Optional[Callable] = None) -> Dict:
        """
        Write JSON data in streaming mode.
        
        Args:
            data: Full data structure
            output_path: Output file path
            progress_callback: Optional callback(percent, message)
            
        Returns:
            Summary of written chunks
        """
        total_files = len(data.get('files', []))
        total_chunks = (total_files + self.chunk_size - 1) // self.chunk_size if total_files > 0 else 1
        chunks_written = 0
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for chunk in self.encoder.stream_json_chunks(data):
                chunk_type = chunk.get('type', 'unknown')
                chunk_info = chunk.get('chunk_info', {})
                
                if chunk_type == 'header':
                    # Write header with first chunk of files
                    header_data = chunk['data']
                    # Get first chunk of files
                    files = data.get('files', [])[:self.chunk_size]
                    header_data['files'] = files
                    
                    json_str = json.dumps(header_data, ensure_ascii=False, indent=2)
                    # Add continuation marker
                    if total_chunks > 1:
                        json_str = json_str[:-2] + ',\n  "_streaming": true,\n  "_chunk_info": ' + \
                                   json.dumps(chunk_info, ensure_ascii=False) + '\n}'
                    
                    f.write(json_str)
                    chunks_written += 1
                    
                    if progress_callback:
                        progress_callback(
                            chunks_written / total_chunks * 100,
                            f"Writing chunk {chunks_written}/{total_chunks}"
                        )
                
                elif chunk_type == 'chunk':
                    # Write subsequent chunks
                    chunk_files = chunk['files']
                    chunk_json = ',\n{\n  "_chunk_index": ' + str(chunk['chunk_index']) + ',\n  "_chunk_info": ' + \
                                json.dumps(chunk_info, ensure_ascii=False) + ',\n  "files": ' + \
                                json.dumps(chunk_files, ensure_ascii=False) + '\n}'
                    f.write(chunk_json)
                    chunks_written += 1
                    
                    if progress_callback:
                        progress_callback(
                            chunks_written / total_chunks * 100,
                            f"Writing chunk {chunks_written}/{total_chunks}"
                        )
                
                elif chunk_type == 'complete':
                    # Close JSON
                    f.write('\n}')
                    
                    if progress_callback:
                        progress_callback(100, "Complete")
        
        return {
            'total_chunks': total_chunks,
            'chunks_written': chunks_written,
            'total_files': total_files
        }
