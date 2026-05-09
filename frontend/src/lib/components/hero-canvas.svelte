<script lang="ts">
	import { onMount } from 'svelte';
	import { mode } from 'mode-watcher';

	type RGB = [number, number, number];

	type ThemeColors = {
		bgA: RGB;
		bgB: RGB;
		neon: RGB;
		dot: RGB;
	};

	const colors: {
		dark: ThemeColors;
		light: ThemeColors;
	} = {
		dark: {
			bgA: [0.01, 0.015, 0.05],
			bgB: [0.03, 0.08, 0.2],
			neon: [0.05, 0.45, 1.0],
			dot: [0.34, 0.48, 1.0]
		},
		light: {
			bgA: [0.973, 0.980, 0.988],
			bgB: [0.886, 0.906, 0.961],
			neon: [0.255, 0.510, 0.965],
			dot: [0.412, 0.541, 0.761]
		}
	};

	function resolveMode(): 'dark' | 'light' {
		if (typeof window === 'undefined') return 'dark';
		try {
			const stored = localStorage.getItem('mode-watcher-mode');
			if (stored === 'light') return 'light';
			if (stored === 'dark') return 'dark';
			return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
		} catch {
			return 'dark';
		}
	}

	let currentMode = $state(resolveMode());

	$effect(() => {
		currentMode = mode.current ?? 'dark';
	});

	let canvas: HTMLCanvasElement;

	const VERT = `
		attribute vec2 a_pos;

		void main() {
			gl_Position = vec4(a_pos, 0.0, 1.0);
		}
	`;

	const FRAG = `
		precision highp float;

		uniform vec2 u_res;
		uniform vec2 u_mouse;
		uniform float u_strength;
		uniform float u_time;

		uniform vec3 u_bgA;
		uniform vec3 u_bgB;
		uniform vec3 u_neon;
		uniform vec3 u_dot;

		float hash(vec2 p) {
			return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
		}

		float noise(vec2 p) {
			vec2 i = floor(p);
			vec2 f = fract(p);

			vec2 u = f * f * (3.0 - 2.0 * f);

			return mix(
				mix(hash(i + vec2(0.0, 0.0)), hash(i + vec2(1.0, 0.0)), u.x),
				mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x),
				u.y
			);
		}

		float fbm(vec2 p) {
			float v = 0.0;
			float a = 0.5;

			for (int i = 0; i < 5; i++) {
				v += a * noise(p);
				p *= 2.0;
				a *= 0.5;
			}

			return v;
		}

		void main() {
			vec2 uv = gl_FragCoord.xy / u_res;
			float ar = u_res.x / u_res.y;

			vec2 p = vec2(uv.x * ar, uv.y);
			vec2 m = vec2(u_mouse.x / u_res.x * ar, u_mouse.y / u_res.y);

			float mouseDist = length(p - m);
			float mouseFlow = smoothstep(0.38, 0.0, mouseDist) * u_strength;

			vec2 flow = p * 2.2;

			flow += vec2(
				fbm(p * 3.0 + vec2(u_time * 0.12, u_time * 0.05)),
				fbm(p * 3.0 - vec2(u_time * 0.06, u_time * 0.14))
			) * 0.45;

			vec2 mouseDir = p - m;
			float len = length(mouseDir);
			mouseDir = len > 0.0001 ? mouseDir / len : vec2(0.0);

			flow += mouseDir * mouseFlow * 0.055;
			flow += vec2(-mouseDir.y, mouseDir.x) * mouseFlow * 0.035;

			float lava =
				fbm(flow * 2.0 + u_time * 0.08) +
				fbm(flow * 4.0 - u_time * 0.05) * 0.45;

			float neonLine = smoothstep(0.48, 0.62, lava) * smoothstep(0.95, 0.64, lava);

			vec3 bg = mix(u_bgA, u_bgB, lava * 0.6);
			bg += u_neon * neonLine * 0.22;

			float gridScale = 35.0;
			vec2 g_uv = uv * vec2(gridScale * ar, gridScale);
			vec2 cell = floor(g_uv);

			float finalMask = 0.0;

			for (int i = -2; i <= 2; i++) {
				for (int j = -2; j <= 2; j++) {
					vec2 nCell = cell + vec2(float(i), float(j));

					vec2 origCenterUV = (nCell + 0.5) / vec2(gridScale * ar, gridScale);
					vec2 origCenterP = vec2(origCenterUV.x * ar, origCenterUV.y);

					vec2 dir = origCenterP - m;
					float dist = length(dir);

					float radius = 0.13;
					float influence = smoothstep(radius, 0.0, dist) * u_strength;

					float push = influence * 0.58;

					vec2 safeDir = dist > 0.0001 ? dir / dist : vec2(0.0);
					vec2 pushedCenterP = origCenterP + safeDir * push * 0.038;

					float d = length(p - pushedCenterP) * gridScale;

					float dotMask = smoothstep(0.085, 0.055, d);

					float fade = 1.0 - influence;
					fade = smoothstep(0.0, 1.0, fade);

					dotMask *= fade;

					finalMask = max(finalMask, dotMask);
				}
			}

			vec3 color = bg + u_dot * finalMask;

			gl_FragColor = vec4(color, 1.0);
		}
	`;

	onMount(() => {
		const gl = canvas.getContext('webgl', { antialias: true });
		if (!gl) return;

		const createShader = (type: number, src: string) => {
			const shader = gl.createShader(type);
			if (!shader) return null;

			gl.shaderSource(shader, src);
			gl.compileShader(shader);

			if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
				console.error(gl.getShaderInfoLog(shader));
				gl.deleteShader(shader);
				return null;
			}

			return shader;
		};

		const vert = createShader(gl.VERTEX_SHADER, VERT);
		const frag = createShader(gl.FRAGMENT_SHADER, FRAG);
		if (!vert || !frag) return;

		const prog = gl.createProgram();
		if (!prog) return;

		gl.attachShader(prog, vert);
		gl.attachShader(prog, frag);
		gl.linkProgram(prog);

		if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
			console.error(gl.getProgramInfoLog(prog));
			return;
		}

		gl.useProgram(prog);

		const vertices = new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]);

		const buffer = gl.createBuffer();
		gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
		gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);

		const pos = gl.getAttribLocation(prog, 'a_pos');
		gl.enableVertexAttribArray(pos);
		gl.vertexAttribPointer(pos, 2, gl.FLOAT, false, 0, 0);

		const uRes = gl.getUniformLocation(prog, 'u_res');
		const uMouse = gl.getUniformLocation(prog, 'u_mouse');
		const uStrength = gl.getUniformLocation(prog, 'u_strength');
		const uTime = gl.getUniformLocation(prog, 'u_time');

		const uBgA = gl.getUniformLocation(prog, 'u_bgA');
		const uBgB = gl.getUniformLocation(prog, 'u_bgB');
		const uNeon = gl.getUniformLocation(prog, 'u_neon');
		const uDot = gl.getUniformLocation(prog, 'u_dot');

		let mouse = {
			x: 0,
			y: 0,
			cx: 0,
			cy: 0
		};

		let strength = 0;
		let targetStrength = 0;
		const start = performance.now();

		const applyColors = () => {
			const active = colors[currentMode];

			gl.uniform3f(uBgA, active.bgA[0], active.bgA[1], active.bgA[2]);
			gl.uniform3f(uBgB, active.bgB[0], active.bgB[1], active.bgB[2]);
			gl.uniform3f(uNeon, active.neon[0], active.neon[1], active.neon[2]);
			gl.uniform3f(uDot, active.dot[0], active.dot[1], active.dot[2]);
		};

		const move = (e: MouseEvent) => {
			const rect = canvas.getBoundingClientRect();

			mouse.x = e.clientX - rect.left;
			mouse.y = rect.height - (e.clientY - rect.top);

			targetStrength = 1;
		};

		const leave = () => {
			targetStrength = 0;
		};

		const resize = () => {
			const dpr = window.devicePixelRatio || 1;

			canvas.width = Math.floor(canvas.clientWidth * dpr);
			canvas.height = Math.floor(canvas.clientHeight * dpr);

			gl.viewport(0, 0, canvas.width, canvas.height);
		};

		window.addEventListener('resize', resize);
		canvas.addEventListener('mousemove', move);
		canvas.addEventListener('mouseleave', leave);

		resize();

		let frame: number;

		const render = () => {
			mouse.cx += (mouse.x - mouse.cx) * 0.055;
			mouse.cy += (mouse.y - mouse.cy) * 0.055;

			strength += (targetStrength - strength) * 0.08;

			const scaleX = canvas.width / canvas.clientWidth;
			const scaleY = canvas.height / canvas.clientHeight;

			applyColors();

			gl.uniform2f(uRes, canvas.width, canvas.height);
			gl.uniform2f(uMouse, mouse.cx * scaleX, mouse.cy * scaleY);
			gl.uniform1f(uStrength, strength);
			gl.uniform1f(uTime, (performance.now() - start) * 0.001);

			gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

			frame = requestAnimationFrame(render);
		};

		render();

		return () => {
			cancelAnimationFrame(frame);
			window.removeEventListener('resize', resize);
			canvas.removeEventListener('mousemove', move);
			canvas.removeEventListener('mouseleave', leave);
		};
	});
</script>

<canvas bind:this={canvas} class="block h-full w-full"></canvas>
