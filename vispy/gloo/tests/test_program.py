# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2014, Nicolas P. Rougier. All rights reserved.
# Distributed under the terms of the new BSD License.
# -----------------------------------------------------------------------------
import unittest

import numpy as np

from vispy import gloo
from vispy.gloo.context import get_current_glir_queue
from vispy.gloo.program import Program
from vispy.testing import run_tests_if_main


def teardown_module():
    # Clear the BS commands that we produced here
    glir = get_current_glir_queue()
    glir.clear()


class ProgramTest(unittest.TestCase):

    def test_init(self):
        
        # Test ok init, no shaders
        program = Program()
        assert program._user_variables == {}
        assert program._code_variables == {}
        assert program._pending_variables == {}
        assert program.shaders == ('', '')
        
        # Test ok init, with shader
        program = Program('A', 'B')
        assert program.shaders == ('A', 'B')
        
        # False inits
        self.assertRaises(ValueError, Program, 'A', None)
        self.assertRaises(ValueError, Program, None, 'B')
        self.assertRaises(ValueError, Program, 3, 'B')
        self.assertRaises(ValueError, Program, 3, None)
        self.assertRaises(ValueError, Program, 'A', 3)
        self.assertRaises(ValueError, Program, None, 3)
        self.assertRaises(ValueError, Program, "", "")
        self.assertRaises(ValueError, Program, "foo", "")
        self.assertRaises(ValueError, Program, "", "foo")
    
    def test_setting_shaders(self):
        program = Program("A", "B")
        assert program.shaders[0] == "A"
        assert program.shaders[1] == "B"
        
        program.set_shaders('C', 'D')
        assert program.shaders[0] == "C"
        assert program.shaders[1] == "D"

    def test_uniform(self):
        
        # Text array unoforms
        program = Program("uniform float A[10];", "foo")
        assert ('uniform', 'float', 'A[0]') in program.variables
        assert len(program.variables) == 10
        
        # Init program
        program = Program("uniform float A;", 
                          "uniform float A; uniform vec4 B;")
        assert ('uniform', 'float', 'A') in program.variables
        assert ('uniform', 'vec4', 'B') in program.variables
        assert len(program.variables) == 2
        
        # Set existing uniforms
        program['A'] = 3.0
        assert isinstance(program['A'], np.ndarray)
        assert program['A'] == 3.0
        assert 'A' in program._user_variables
        #
        program['B'] = 1.0, 2.0, 3.0, 4.0
        assert isinstance(program['B'], np.ndarray)
        assert all(program['B'] == np.array((1.0, 2.0, 3.0, 4.0), np.float32))
        assert 'B' in program._user_variables
        
        # Set non-exisint uniforms
        program['C'] = 1.0, 2.0
        assert program['C'] == (1.0, 2.0)
        assert 'C' not in program._user_variables
        assert 'C' in program._pending_variables
        
        # Set samplers
        program.set_shaders("uniform sampler2D T2; uniform sampler3D T3;", "f")
        program['T2'] = np.zeros((10, 10), np.float32)
        program['T3'] = np.zeros((10, 10, 10), np.float32)
        assert isinstance(program['T2'], gloo.Texture2D)
        assert isinstance(program['T3'], gloo.Texture3D)
        
        # Set samplers with textures
        tex = gloo.Texture2D((10, 10))
        program['T2'] = tex
        assert program['T2'] is tex
        program['T2'] = np.zeros((10, 10), np.float32)  # Update texture
        assert program['T2'] is tex
        
        # C should be taken up when code comes along that mentions it
        program.set_shaders("uniform float A; uniform vec2 C;", 
                            "uniform float A; uniform vec4 B;")
        assert isinstance(program['C'], np.ndarray)
        assert all(program['C'] == np.array((1.0, 2.0), np.float32))
        assert 'C' in program._user_variables
        assert 'C' not in program._pending_variables
        
        # Set wrong values
        self.assertRaises(ValueError, program.__setitem__, 'A', (1.0, 2.0))
        self.assertRaises(ValueError, program.__setitem__, 'B', (1.0, 2.0))
        self.assertRaises(ValueError, program.__setitem__, 'C', 1.0)
        
        # Set wrong values beforehand
        program['D'] = 1.0, 2.0
        self.assertRaises(ValueError, program.set_shaders, 
                          '', 'uniform vec3 D;')
    
    def test_attributes(self):
        program = Program("attribute float A; attribute vec4 B;", "foo")
        assert ('attribute', 'float', 'A') in program.variables
        assert ('attribute', 'vec4', 'B') in program.variables
        assert len(program.variables) == 2
        
        from vispy.gloo import VertexBuffer
        vbo = VertexBuffer()
        
        # Set existing uniforms
        program['A'] = vbo
        assert program['A'] == vbo
        assert 'A' in program._user_variables
        assert program._user_variables['A'] is vbo
        
        # Set data - update existing vbp
        program['A'] = np.zeros((10,), np.float32)
        assert program._user_variables['A'] is vbo
        
        # Set data - create new vbo
        program['B'] = np.zeros((10, 4), np.float32)
        assert isinstance(program._user_variables['B'], VertexBuffer)
        
        # Set non-exisint uniforms
        program['C'] = vbo
        assert program['C'] == vbo
        assert 'C' not in program._user_variables
        assert 'C' in program._pending_variables
        
        # C should be taken up when code comes along that mentions it
        program.set_shaders("attribute float A; attribute vec2 C;", "foo")
        assert program['C'] == vbo
        assert 'C' in program._user_variables
        assert 'C' not in program._pending_variables
        
        # Set wrong values
        self.assertRaises(ValueError, program.__setitem__, 'A', 'asddas')
        
        # Set wrong values beforehand
        program['D'] = ""
        self.assertRaises(ValueError, program.set_shaders, 
                          'attribute vec3 D;', '')
        
        # Set to one value per vertex
        program.set_shaders("attribute float A; attribute vec2 C;", "foo")
        program['A'] = 1.0
        assert program['A'] == 1.0
        program['C'] = 1.0, 2.0 
        assert all(program['C'] == np.array((1.0, 2.0), np.float32))
        #
        self.assertRaises(ValueError, program.__setitem__, 'A', (1.0, 2.0))
        self.assertRaises(ValueError, program.__setitem__, 'C', 1.0)
        self.assertRaises(ValueError, program.bind, 'notavertexbuffer')
    
    def test_vbo(self):
        # Test with count
        program = Program('attribute float a; attribute vec2 b;', 'foo', 10)
        assert program._count == 10
        assert ('attribute', 'float', 'a') in program.variables
        assert ('attribute', 'vec2', 'b') in program.variables
        
        # Set
        program['a'] = np.ones((10,), np.float32)
        assert np.all(program._buffer['a'] == 1)
        
    def test_vayings(self):
        
        # Varyings and constants are detected
        program = Program("varying float A; const vec4 B;", "foo")
        assert ('varying', 'float', 'A') in program.variables
        assert ('const', 'vec4', 'B') in program.variables
        
        # But cannot be set
        self.assertRaises(KeyError, program.__setitem__, 'A', 3.0)
        self.assertRaises(KeyError, program.__setitem__, 'B', (1.0, 2.0, 3.0))
        # And anything else also fails
        self.assertRaises(KeyError, program.__getitem__, 'fooo')
    
    def test_draw(self):
        # Init
        program = Program("attribute float A;", "uniform float foo")
        program['A'] = np.zeros((10,), np.float32)
        
        # We need to disable flushing to run this test
        flush = program._glir.flush
        program._glir.flush = lambda x=None: None
        
        try:
            # Draw arrays
            program.draw('triangles')
            glir_cmd = program._glir.clear()[-1]
            assert glir_cmd[0] == 'DRAW'
            assert len(glir_cmd[-1]) == 2
            
            # Draw elements
            indices = gloo.IndexBuffer(np.zeros(10, dtype=np.uint8))
            program.draw('triangles', indices)
            glir_cmd = program._glir.clear()[-1]
            assert glir_cmd[0] == 'DRAW'
            assert len(glir_cmd[-1]) == 3
            
            # Invalid mode
            self.assertRaises(ValueError, program.draw, 'nogeometricshape')
            # Invalid index
            self.assertRaises(TypeError, program.draw, 'triangles', 'notindex')
            # No atributes
            program = Program("attribute float A;", "uniform float foo")
            self.assertRaises(RuntimeError, program.draw, 'triangles')
            # Atributes with different sizes
            program = Program("attribute float A; attribute float B;", "foo")
            program['A'] = np.zeros((10,), np.float32)
            program['B'] = np.zeros((11,), np.float32)
            self.assertRaises(RuntimeError, program.draw, 'triangles')
        
        finally:
            program._glir.flush = flush

run_tests_if_main()
