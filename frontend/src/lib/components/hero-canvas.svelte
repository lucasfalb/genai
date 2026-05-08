<script lang="ts">
	import { onMount } from 'svelte';

	let canvas: HTMLCanvasElement;

	const VERT = `
attribute vec2 a_pos;
void main() {
    gl_Position = vec4(a_pos, 0.0, 1.0);
}`;

	const FRAG = `
precision mediump float;
uniform float u_time;
uniform vec2 u_res;
uniform vec2 u_mouse;

void main() {
    vec2 uv = gl_FragCoord.xy / u_res;
    float ar = u_res.x / u_res.y;
    vec2 p = vec2(uv.x * ar, uv.y);
    float t = u_time * 0.3;

    // Animated blob centers
    vec2 c0 = vec2((0.30 + 0.20 * sin(t * 1.10)) * ar, 0.52 + 0.22 * cos(t * 0.85));
    vec2 c1 = vec2((0.68 + 0.17 * cos(t * 0.75)) * ar, 0.30 + 0.20 * sin(t * 1.15));
    vec2 c2 = vec2((0.50 + 0.22 * sin(t * 0.55 + 1.5)) * ar, 0.74 + 0.16 * cos(t * 0.95));
    vec2 c3 = vec2((0.18 + 0.12 * cos(t * 1.25)) * ar, 0.22 + 0.14 * sin(t * 0.65));
    vec2 c4 = vec2((0.82 + 0.12 * sin(t * 0.90 + 2.0)) * ar, 0.65 + 0.18 * cos(t * 1.05));

    // Mouse influence
    vec2 m = vec2(u_mouse.x / u_res.x * ar, 1.0 - u_mouse.y / u_res.y);

    // Metaball scalar field
    float f = 0.0;
    f += 0.024 / max(dot(p - c0, p - c0), 0.0001);
    f += 0.018 / max(dot(p - c1, p - c1), 0.0001);
    f += 0.020 / max(dot(p - c2, p - c2), 0.0001);
    f += 0.013 / max(dot(p - c3, p - c3), 0.0001);
    f += 0.015 / max(dot(p - c4, p - c4), 0.0001);
    f += 0.006 / max(dot(p - m,  p - m),  0.0001);

    // Exponential color weights per blob
    float d0 = length(p - c0);
    float d1 = length(p - c1);
    float d2 = length(p - c2);
    float d3 = length(p - c3);
    float d4 = length(p - c4);

    // App palette
    vec3 bg     = vec3(0.031, 0.031, 0.063); // #080810
    vec3 blue   = vec3(0.376, 0.647, 0.980); // blue-400
    vec3 cyan   = vec3(0.133, 0.827, 0.937); // cyan-400
    vec3 violet = vec3(0.655, 0.545, 0.980); // violet-400
    vec3 indigo = vec3(0.506, 0.549, 0.980); // indigo-400

    float k = 5.0;
    float w0 = exp(-d0 * k);
    float w1 = exp(-d1 * k);
    float w2 = exp(-d2 * k);
    float w3 = exp(-d3 * k);
    float w4 = exp(-d4 * k);
    float wt = w0 + w1 + w2 + w3 + w4 + 0.0001;

    vec3 blobCol = (blue * w0 + cyan * w1 + mix(blue, cyan, 0.4) * w2 + violet * w3 + indigo * w4) / wt;

    float glow = smoothstep(0.4, 2.5, f);
    float aura = smoothstep(0.0, 0.6, f * 0.3);

    vec3 col = bg;
    col += blobCol * glow * 0.55;
    col += (blue * 0.4 + cyan * 0.4 + violet * 0.2) * aura * 0.08;

    // Subtle surface shimmer
    float shimmer = sin(p.x * 9.0 + t) * cos(p.y * 9.0 + t * 0.7) * 0.012;
    col += blobCol * shimmer * glow;

    // Edge vignette
    float vig = 1.0 - 0.5 * smoothstep(0.2, 1.1, length(uv - 0.5) * 1.8);
    col *= vig;

    gl_FragColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}`;

	onMount(() => {
		const gl = canvas.getContext('webgl');
		if (!gl) return;

		function makeShader(type: number, src: string) {
			const s = gl!.createShader(type)!;
			gl!.shaderSource(s, src);
			gl!.compileShader(s);
			return s;
		}

		const program = gl.createProgram()!;
		gl.attachShader(program, makeShader(gl.VERTEX_SHADER, VERT));
		gl.attachShader(program, makeShader(gl.FRAGMENT_SHADER, FRAG));
		gl.linkProgram(program);
		gl.useProgram(program);

		const buf = gl.createBuffer();
		gl.bindBuffer(gl.ARRAY_BUFFER, buf);
		gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);

		const posLoc = gl.getAttribLocation(program, 'a_pos');
		gl.enableVertexAttribArray(posLoc);
		gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);

		const timeLoc = gl.getUniformLocation(program, 'u_time');
		const resLoc = gl.getUniformLocation(program, 'u_res');
		const mouseLoc = gl.getUniformLocation(program, 'u_mouse');

		const mouse = [0, 0];
		const onMouseMove = (e: MouseEvent) => {
			const dpr = window.devicePixelRatio || 1;
			mouse[0] = e.clientX * dpr;
			mouse[1] = canvas.height - e.clientY * dpr;
		};
		window.addEventListener('mousemove', onMouseMove);

		let raf: number;

		function resize() {
			const dpr = window.devicePixelRatio || 1;
			canvas.width = canvas.offsetWidth * dpr;
			canvas.height = canvas.offsetHeight * dpr;
			gl!.viewport(0, 0, canvas.width, canvas.height);
			gl!.uniform2f(resLoc, canvas.width, canvas.height);
		}

		const ro = new ResizeObserver(resize);
		ro.observe(canvas);
		resize();

		function render(time: number) {
			gl!.uniform1f(timeLoc, time * 0.001);
			gl!.uniform2f(mouseLoc, mouse[0], mouse[1]);
			gl!.drawArrays(gl!.TRIANGLE_STRIP, 0, 4);
			raf = requestAnimationFrame(render);
		}
		raf = requestAnimationFrame(render);

		return () => {
			cancelAnimationFrame(raf);
			ro.disconnect();
			window.removeEventListener('mousemove', onMouseMove);
		};
	});
</script>

<canvas bind:this={canvas} class="absolute inset-0 size-full"></canvas>
