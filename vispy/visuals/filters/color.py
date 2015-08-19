# -*- coding: utf-8 -*-
# Copyright (c) 2015, Vispy Development Team.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.

import weakref

from ..shaders import Function, Varying
from ...color import colormap, Color

class Isoline(object):
    def __init__(self, level=1., width=1.0, color='black', antialias=1.0):
        self.vshader = Function("""
            void position_support()
            {
                $coords = $position.z;
            }
        """)

        self.fshader = Function("""
            void isoline() {
                // function taken from glumpy/examples/isocurves.py
                // and extended to have level, width and color as parameters

                // Extract data value
                vec3 val3 = gl_FragColor.rgb;
                //vec3 val3 = $coords.rgb;


                const vec3 w = vec3(0.299, 0.587, 0.114);
                //const vec3 w = vec3(0.2126, 0.7152, 0.0722);
                //float value = dot(gl_FragColor.rgb, w);

                //float value = dot(val3, w);
                float value = $coords;


                // setup lw, aa
                float linewidth = $isowidth + $antialias;

                // "middle" contour(s) dividing upper and lower half
                // but only if isolevel is even
                if( mod($isolevel,2.0) == 0.0 ) {
                    if( length(value - 0.5) < 0.5 / $isolevel)
                        linewidth = linewidth * 2;
                }

                // Trace contouriso
                float v  = $isolevel * value - 0.5;
                vec3 v3  = $isolevel * val3 - 0.5;

                float dv = linewidth/2.0 * fwidth(v);
                vec3 dv3 = linewidth/2.0 * fwidth(v3);

                float f = abs(fract(v) - 0.5);
                vec3 f3 = abs(fract(v3) - 0.5);

                float d = smoothstep(-dv, +dv, f);
                vec3 d3 = smoothstep(-dv3, +dv3, f3);

                float t = linewidth/2.0 - $antialias;

                d = abs(d)*linewidth/2.0 - t;
                //float d = d3.x * d3.y *d3.z *linewidth/2.0 - t;

                if( d < - linewidth ) {
                    d = 1.0;
                } else  {
                     d /= $antialias;
                }

                vec4 bg = $color_transform1(gl_FragColor);

                vec4 fc = vec4($isocolor.rgb, 0);

                if (d < 1.) {
                    fc.a = 1-d;
                }

                gl_FragColor = mix(bg, fc, fc.a);

            }
        """)
        self.level = level
        self.width = width
        self.color = color
        self.antialias = antialias
        self.vshader['coords'] = Varying('coords', dtype='float')
        self.fshader['coords'] = self.vshader['coords']

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, l):
        self._level = l
        self.fshader['isolevel'] = l

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, w):
        self._width = w
        self.fshader['isowidth'] = w

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, c):
        self._color = c
        self.fshader['isocolor'] = Color(c).rgba

    @property
    def antialias(self):
        return self._antialias

    @antialias.setter
    def antialias(self, a):
        self._antialias = a
        self.fshader['antialias'] = a

    def _attach(self, visual):
        visual._get_hook('vert', 'post').add(self.vshader())
        visual._get_hook('frag', 'post').add(self.fshader())

        try:
            # this works for single and multi channel data
            self.fshader['color_transform1'] = \
                visual.shared_program.frag['color_transform']
            visual.shared_program.frag['color_transform'] = \
                Function('vec4 pass(vec4 color) { return color; }')
        except:
            self.fshader['color_transform1'] = \
                Function('vec4 pass(vec4 color) { return color; }')

        self.vshader['position'] = visual.shared_program.vert['position']


class Alpha(object):
    def __init__(self, alpha=1.0):
        self.shader = Function("""
            void apply_alpha() {
                gl_FragColor.a = gl_FragColor.a * $alpha;
            }
        """)
        self.alpha = alpha
    
    @property
    def alpha(self):
        return self._alpha
    
    @alpha.setter
    def alpha(self, a):
        self._alpha = a
        self.shader['alpha'] = a
        
    def _attach(self, visual):
        self._visual = weakref.ref(visual)
        hook = visual._get_hook('frag', 'post')
        hook.add(self.shader())


class ColorFilter(object):
    def __init__(self, filter=(1, 1, 1, 1)):
        self.shader = Function("""
            void apply_color_filter() {
                gl_FragColor = gl_FragColor * $filter;
            }
        """)
        self.filter = filter
    
    @property
    def filter(self):
        return self._filter
    
    @filter.setter
    def filter(self, f):
        self._filter = tuple(f)
        self.shader['filter'] = self._filter
        
    def _attach(self, visual):
        self._visual = visual
        hook = visual._get_hook('frag', 'post')
        hook.add(self.shader(), position=8)


class ZColormapFilter(object):
    def __init__(self, cmap, zrange=(0, 1)):
        self.vshader = Function("""
            void z_colormap_support() {
                $zval = $position.z;
            }
        """)
        self.fshader = Function("""
            void apply_z_colormap() {
                gl_FragColor = $cmap(($zval - $zrange.x) / 
                                     ($zrange.y - $zrange.x));
            }
        """)
        if isinstance(cmap, str):
            cmap = colormap.get_colormap(cmap)
        self.cmap = Function(cmap.glsl_map)
        self.fshader['cmap'] = self.cmap
        self.fshader['zrange'] = zrange
        self.vshader['zval'] = Varying('v_zval', dtype='float')
        self.fshader['zval'] = self.vshader['zval']
        
    def _attach(self, visual):
        self._visual = visual
        vhook = visual._get_hook('vert', 'post')
        vhook.add(self.vshader(), position=9)
        fhook = visual._get_hook('frag', 'post')
        fhook.add(self.fshader(), position=3)
        
        self.vshader['position'] = visual.shared_program.vert['position']
