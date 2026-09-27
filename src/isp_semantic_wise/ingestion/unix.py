"""
Unix Shell Script Connector - Parses ksh/bash scripts
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from loguru import logger

from .base import BaseIngestionConnector, IngestionResult


class UnixConnector(BaseIngestionConnector):
    """Connector for Unix shell scripts (ksh, bash, sh)"""
    
    SUPPORTED_EXTENSIONS = {".ksh", ".sh", ".bash", ".csh"}
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.scripts_path = Path(config.get("scripts_path", "/data/scripts"))
        self.file_patterns = config.get("file_patterns", ["*.ksh", "*.sh", "*.bash"])
        self.extract_variables = config.get("extract_variables", True)
        self.extract_commands = config.get("extract_commands", True)
        self.trace_data_flow = config.get("trace_data_flow", True)
    
    def discover(self) -> List[str]:
        """Discover shell scripts"""
        files = []
        for pattern in self.file_patterns:
            files.extend(self.scripts_path.rglob(pattern))
        return [str(f) for f in files]
    
    def extract(self, source: str) -> List[Dict[str, Any]]:
        """Extract content from shell script"""
        path = Path(source)
        content = path.read_text(encoding='utf-8', errors='ignore')
        
        return [{
            "artifact_type": "shell_script",
            "name": path.stem,
            "source_system": "unix",
            "path": str(path.relative_to(self.scripts_path)),
            "code_snippet": content,
            "metadata": {
                "file_path": str(path),
                "file_size": len(content),
                "shebang": self._extract_shebang(content),
            },
        }]
    
    def _extract_shebang(self, content: str) -> str:
        """Extract shebang line"""
        lines = content.split('\n')
        if lines and lines[0].startswith('#!'):
            return lines[0].strip()
        return ""
    
    def transform(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform shell scripts to standard artifacts"""
        transformed = []
        
        for item in raw_data:
            content = item["code_snippet"]
            
            # Base artifact
            base_artifact = {
                "artifact_type": item["artifact_type"],
                "name": item["name"],
                "source_system": "unix",
                "path": item["path"],
                "code_snippet": item["code_snippet"],
                "metadata": item["metadata"],
            }
            transformed.append(base_artifact)
            
            # Extract variables
            if self.extract_variables:
                variables = self._extract_variables(content)
                for var in variables:
                    transformed.append({
                        "artifact_type": "variable",
                        "name": var["name"],
                        "source_system": "unix",
                        "path": f"{item['path']}/{var['name']}",
                        "code_snippet": var["declaration"],
                        "metadata": {
                            "script_path": item["path"],
                            "var_type": var["type"],
                            "value": var.get("value", ""),
                        },
                    })
            
            # Extract commands/calls
            if self.extract_commands:
                commands = self._extract_commands(content)
                for cmd in commands:
                    transformed.append({
                        "artifact_type": "command_call",
                        "name": cmd["command"],
                        "source_system": "unix",
                        "path": f"{item['path']}/{cmd['command']}",
                        "code_snippet": cmd["full_line"],
                        "metadata": {
                            "script_path": item["path"],
                            "args": cmd.get("args", []),
                            "type": cmd["type"],
                        },
                    })
            
            # Trace data flow
            if self.trace_data_flow:
                data_flows = self._trace_data_flow(content)
                for flow in data_flows:
                    transformed.append({
                        "artifact_type": "data_flow",
                        "name": f"{flow['source']} -> {flow['target']}",
                        "source_system": "unix",
                        "path": f"{item['path']}/{flow['source']}->{flow['target']}",
                        "code_snippet": flow["context"],
                        "metadata": {
                            "script_path": item["path"],
                            "flow_type": flow["type"],
                        },
                    })
        
        return transformed
    
    def _extract_variables(self, content: str) -> List[Dict]:
        """Extract variable declarations and assignments"""
        variables = []
        
        # Patterns for variable declarations
        patterns = [
            # VAR=value
            r'^(\w+)=([^#\n]*)',
            # export VAR=value
            r'^export\s+(\w+)=([^#\n]*)',
            # readonly VAR=value
            r'^readonly\s+(\w+)=([^#\n]*)',
            # local VAR=value
            r'^local\s+(\w+)=([^#\n]*)',
            # declare VAR=value
            r'^declare\s+(\w+)=([^#\n]*)',
        ]
        
        for line_num, line in enumerate(content.split('\n'), 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    var_name = match.group(1)
                    var_value = match.group(2).strip().strip('"\'')
                    var_type = "exported" if 'export' in line else "local"
                    
                    variables.append({
                        "name": var_name,
                        "type": var_type,
                        "value": var_value,
                        "declaration": line,
                        "line_number": line_num,
                    })
                    break
        
        return variables
    
    def _extract_commands(self, content: str) -> List[Dict]:
        """Extract command calls from script"""
        commands = []
        
        # Pattern for command calls
        # Skip variable assignments, comments, control structures
        skip_patterns = [
            r'^\s*#',
            r'^\s*$',
            r'^\s*(if|then|else|elif|fi|for|while|do|done|case|esac)\b',
            r'^\s*(function\s+\w+|\(\))\s*\{?',
        ]
        
        command_pattern = r'^\s*(\w+)\s+(.+)$'
        
        for line_num, line in enumerate(content.split('\n'), 1):
            line = line.strip()
            if not line:
                continue
            
            # Skip non-command lines
            skip = False
            for pattern in skip_patterns:
                if re.match(pattern, line):
                    skip = True
                    break
            if skip:
                continue
            
            match = re.match(command_pattern, line)
            if match:
                cmd = match.group(1)
                args = match.group(2).strip()
                
                # Classify command type
                cmd_type = self._classify_command(cmd)
                
                commands.append({
                    "command": cmd,
                    "args": args,
                    "full_line": line,
                    "type": cmd_type,
                    "line_number": line_num,
                })
        
        return commands
    
    def _classify_command(self, cmd: str) -> str:
        """Classify command type"""
        builtin = {'cd', 'echo', 'printf', 'read', 'export', 'unset', 'alias', 'unalias'}
        file_ops = {'cp', 'mv', 'rm', 'mkdir', 'rmdir', 'ls', 'find', 'tar', 'gzip', 'gunzip'}
        db_ops = {'sqlplus', 'sqlldr', 'expdp', 'impdp', 'rman'}
        etl_ops = {'air', 'abinitio', 'mpirun', 'm_job'}
        sched = {'cron', 'at', 'batch', 'nohup'}
        
        if cmd in builtin:
            return "builtin"
        elif cmd in file_ops:
            return "file_operation"
        elif cmd in db_ops:
            return "database"
        elif cmd in etl_ops:
            return "etl"
        elif cmd in sched:
            return "scheduler"
        else:
            return "external"
    
    def _trace_data_flow(self, content: str) -> List[Dict]:
        """Trace data flow through script"""
        flows = []
        
        # Look for input/output redirections, pipes, file operations
        patterns = {
            'input_redirect': r'(\w+)\s*<\s*(\S+)',
            'output_redirect': r'(\w+)\s*>\s*(\S+)',
            'append_redirect': r'(\w+)\s*>>\s*(\S+)',
            'pipe': r'(\w+)\s*\|\s*(\w+)',
            'file_read': r'(cat|read|while\s+read)\s+(\S+)',
            'file_write': r'(echo|printf|tee)\s+.*>\s*(\S+)',
        }
        
        for line_num, line in enumerate(content.split('\n'), 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            for flow_type, pattern in patterns.items():
                matches = re.findall(pattern, line)
                for match in matches:
                    if isinstance(match, tuple) and len(match) == 2:
                        flows.append({
                            "source": match[0],
                            "target": match[1],
                            "type": flow_type,
                            "context": line,
                            "line_number": line_num,
                        })
        
        return flows
    
    def load(self, transformed_data: List[Dict[str, Any]]) -> IngestionResult:
        """Load to storage"""
        return IngestionResult(
            job_id=self.job.job_id if self.job else "",
            success=True,
            items=transformed_data,
        )