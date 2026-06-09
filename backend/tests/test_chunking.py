import pytest
from src.services.chunking_service import ChunkingService


def test_python_chunker():
    code = (
        "import os\n\n"
        "class MyClass:\n"
        "    def method(self):\n"
        "        pass\n\n"
        "def helper_func():\n"
        "    return 42\n"
    )
    chunks = ChunkingService.chunk_file("test.py", code, "Python")
    
    chunk_types = [c["chunk_type"] for c in chunks]
    assert "class" in chunk_types
    assert "function" in chunk_types
    assert "module" in chunk_types
    
    # Class chunk should match class boundaries
    class_chunk = next(c for c in chunks if c["chunk_type"] == "class")
    assert class_chunk["start_line"] == 3
    assert class_chunk["end_line"] == 5


def test_typescript_chunker():
    code = (
        "import React from 'react';\n\n"
        "export function Header(props: any) {\n"
        "    return <h1>{props.title}</h1>;\n"
        "}\n\n"
        "export const regularHelper = () => {\n"
        "    return 'hello';\n"
        "}\n"
    )
    chunks = ChunkingService.chunk_file("Header.tsx", code, "TypeScript")
    
    chunk_types = [c["chunk_type"] for c in chunks]
    assert "component" in chunk_types  # Header has capital H, so component
    assert "function" in chunk_types   # regularHelper is lowercase, so function
    
    comp_chunk = next(c for c in chunks if c["chunk_type"] == "component")
    assert comp_chunk["start_line"] == 3
    assert comp_chunk["end_line"] == 5


def test_java_chunker():
    code = (
        "package com.test;\n\n"
        "public class Main {\n"
        "    public static void main(String[] args) {\n"
        "        System.out.println(\"Hello\");\n"
        "    }\n"
        "}\n"
    )
    chunks = ChunkingService.chunk_file("Main.java", code, "Java")
    
    chunk_types = [c["chunk_type"] for c in chunks]
    assert "class" in chunk_types
    assert "method" in chunk_types
    
    method_chunk = next(c for c in chunks if c["chunk_type"] == "method")
    assert method_chunk["start_line"] == 4
    assert method_chunk["end_line"] == 6


def test_go_chunker():
    code = (
        "package main\n\n"
        "type User struct {\n"
        "    Name string\n"
        "}\n\n"
        "func GetUser() *User {\n"
        "    return &User{Name: \"Alice\"}\n"
        "}\n"
    )
    chunks = ChunkingService.chunk_file("main.go", code, "Go")
    
    chunk_types = [c["chunk_type"] for c in chunks]
    assert "struct" in chunk_types
    assert "function" in chunk_types
    
    struct_chunk = next(c for c in chunks if c["chunk_type"] == "struct")
    assert struct_chunk["start_line"] == 3
    assert struct_chunk["end_line"] == 5
