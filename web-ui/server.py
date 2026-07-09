#!/usr/bin/env python3
"""
Repo JSON Generator - Web UI Server

A lightweight HTTP server that bridges the web interface with the generator API.
Provides API endpoints to execute generator commands and return results.

Usage:
    python3 web-ui/server.py [port]
"""

import json
import os
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from git.repository import RepoJSONGenerator


class GeneratorHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Generator API"""

    def do_OPTIONS(self):
        """Handle CORS preflight for extension requests."""
        parsed_path = urlparse(self.path)
        if parsed_path.path.startswith('/api/'):
            self.send_response(204)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
        else:
            self.send_error(404)

    def do_GET(self):
        """Handle GET requests - serve the web interface and API"""
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/' or parsed_path.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()

            html_path = os.path.join(os.path.dirname(__file__), 'index.html')
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            self.wfile.write(html_content.encode('utf-8'))

        elif parsed_path.path == '/api/status':
            self._send_json_response(200, {
                'success': True,
                'hasToken': bool(os.environ.get('GITHUB_TOKEN')),
            })

        elif parsed_path.path == '/api/branches':
            query_params = parse_qs(parsed_path.query)
            repo = query_params.get('repo', [''])[0]

            if not repo:
                self._send_json_response(400, {'success': False, 'error': 'Repository URL is required'})
                return

            try:
                result = self._get_generator().get_branches(repo)
                self._send_json_response(200, {
                    'success': True,
                    'branches': result['branches'],
                    'count': result['count'],
                    'repository': result['repository'],
                })
            except Exception as e:
                self._send_json_response(500, {'success': False, 'error': str(e)})

        elif parsed_path.path in ('/api/commits', '/api/versions'):
            query_params = parse_qs(parsed_path.query)
            repo = query_params.get('repo', [''])[0]
            branch = query_params.get('branch', [''])[0]
            limit = query_params.get('limit', ['30'])[0]

            if not repo or not branch:
                self._send_json_response(400, {
                    'success': False,
                    'error': 'Repository URL and branch are required',
                })
                return

            try:
                limit_value = int(limit)
            except ValueError:
                self._send_json_response(400, {'success': False, 'error': 'limit must be an integer'})
                return

            try:
                result = self._get_generator().get_branch_versions(repo, branch, limit=limit_value)
                commits = [
                    {
                        'hash': version['hash'],
                        'message': version['message'],
                        'short_hash': version['short_hash'],
                        'date': version['date'],
                    }
                    for version in result['versions']
                ]
                self._send_json_response(200, {
                    'success': True,
                    'repository': result['repository'],
                    'branch': result['branch'],
                    'limit': result['limit'],
                    'count': result['count'],
                    'commits': commits,
                    'versions': result['versions'],
                })
            except Exception as e:
                self._send_json_response(500, {'success': False, 'error': str(e)})

        else:
            self.send_error(404, f"Not found: {self.path}")

    def do_POST(self):
        """Handle POST requests - execute generator commands"""
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/api/generate':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length)
                request_data = json.loads(body.decode('utf-8'))

                repo = request_data.get('repo', '')
                if not repo:
                    self._send_json_response(400, {
                        'success': False,
                        'error': 'Repository URL is required',
                    })
                    return

                command = request_data.get('command', 'sync')
                if command not in ('sync', 'info', 'full'):
                    self._send_json_response(400, {
                        'success': False,
                        'error': f'Unknown command: {command}',
                    })
                    return

                try:
                    result = self._run_generate(request_data)
                    self._send_json_response(200, result)
                except Exception as e:
                    self._send_json_response(200, {
                        'success': False,
                        'error': str(e),
                        'data': None,
                        'meta': {
                            'command': request_data.get('command', 'sync'),
                            'repo': request_data.get('repo', ''),
                            'branch': request_data.get('branch', 'main'),
                        },
                    })

            except json.JSONDecodeError:
                self._send_json_response(400, {
                    'success': False,
                    'error': 'Invalid JSON in request body',
                })
            except Exception as e:
                self._send_json_response(500, {
                    'success': False,
                    'error': str(e),
                })
        else:
            self.send_error(404, f"Not found: {self.path}")

    def _run_generate(self, params: dict) -> dict:
        """Run generate command via RepoJSONGenerator and return structured JSON."""
        start_time = time.time()
        command = params.get('command', 'sync')
        repo = params['repo']
        branch = params.get('branch', 'main')
        commit = (params.get('commit') or '').strip()
        file_filter = (params.get('filter') or '').strip() or None
        exclude_filter = (params.get('exclude') or '').strip() or None
        max_files = int(params.get('maxFiles', 50))

        generator = self._get_generator()

        if not commit:
            commit = generator.resolve_latest_commit(repo, branch)

        if command == 'sync':
            data = generator.get_commit_full_changes(
                repo_url=repo,
                commit=commit,
                branch=branch,
                file_filter=file_filter,
                exclude_filter=exclude_filter,
                command_type='sync',
            )
        elif command == 'info':
            data = generator.get_commit_diff_info(
                repo_url=repo,
                commit=commit,
                branch=branch,
                file_filter=file_filter,
                exclude_filter=exclude_filter,
            )
        elif command == 'full':
            data = generator.get_full_repo_content(
                repo_url=repo,
                commit=commit,
                branch=branch,
                file_filter=file_filter,
                exclude_filter=exclude_filter,
                max_files=max_files,
                command_type='full',
            )
        else:
            raise ValueError(f'Unknown command: {command}')

        duration = round(time.time() - start_time, 1)
        return {
            'success': True,
            'data': data,
            'meta': {
                'command': command,
                'duration': duration,
                'repo': repo,
                'branch': branch,
                'commit': commit,
            },
        }

    def _send_json_response(self, status_code, data):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _get_generator(self):
        """Create a repository generator with optional GitHub token."""
        token = os.environ.get('GITHUB_TOKEN')
        return RepoJSONGenerator(token=token, verbose=False)

    def log_message(self, format, *args):
        """Custom log format"""
        print(f"[{self.log_date_time_string()}] {format % args}")


def run_server(port=8080):
    """Start the HTTP server"""
    server = HTTPServer(('0.0.0.0', port), GeneratorHandler)
    print("=" * 60)
    print("  Repo JSON Generator - Web UI")
    print("=" * 60)
    print()
    print(f"  Server running at:")
    print(f"    → Local: http://localhost:{port}")
    print(f"    → Network: http://0.0.0.0:{port}")
    print()
    print(f"  Press Ctrl+C to stop")
    print("=" * 60)
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        server.shutdown()


if __name__ == '__main__':
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port number: {sys.argv[1]}, using default 8080")

    run_server(port)
