(async () => {
	// =====================================================================
	// CONFIG
	// =====================================================================

	// List of can targets to click, in the order they should be clicked.
	// Coordinates are UV percentages (0..100) on the equirectangular WebP
	// background. The values below were copied from payload.json
	// (scene 0, "coordinates" array).
	const CANS = [
		{ x: 25.31, y: 60.35, name: "can-bag" },
		{ x: 67.68, y: 37.01, name: "can-ban" },
		{ x: 90.54, y: 37.03, name: "can-basket" },
		{ x: 1.59, y: 58.06, name: "can-bike" },
		{ x: 81.94, y: 31.51, name: "can-dancing" },
		{ x: 37.36, y: 57.25, name: "can-diver" },
		{ x: 70.58, y: 55.73, name: "can-hand" },
		{ x: 50.42, y: 65.74, name: "can-sign" },
		{ x: 44.13, y: 37.41, name: "can-surfer" },
		{ x: 61.27, y: 21.97, name: "can-ufo" },
	];

	const DELAY_MS = 25;

	// =====================================================================
	// INTERNALS (no need to edit below)
	// =====================================================================

	// Vertical FOV of the THREE.PerspectiveCamera created by the game.
	// This matches the bundled constant ($g = 75 in custom-script-1.js).
	const FOV_V = (75 * Math.PI) / 180;

	const wait = (ms) => new Promise((r) => setTimeout(r, ms));

	// Shape test for the game instance. The class is minified in the
	// bundle (as "xv") so we identify it by the methods/properties it
	// carries rather than by name.
	const isGame = (o) => {
		try {
			return (
				o &&
				typeof o === "object" &&
				o.cameraController &&
				o.interactionHandler &&
				o.itemManager &&
				o.panoramaSphere &&
				typeof o.click === "function"
			);
		} catch {
			return false;
		}
	};

	// The game is ready to be played once the panorama mesh has been
	// built, its items have been added, and the fixed-step render loop
	// is running.
	const isReady = (g) => {
		try {
			return (
				isGame(g) &&
				g.isRunning &&
				g.panoramaSphere.sphere &&
				g.itemManager.getItems().length > 0
			);
		} catch {
			return false;
		}
	};

	// The game canvas is the one with touch-action: none (set by the
	// game so it can capture pointer drags without the browser
	// hijacking them) and a non-zero rendered size.
	function findCanvas() {
		return (
			[...document.querySelectorAll("canvas")].find(
				(c) =>
					c.style.touchAction === "none" &&
					c.width > 0 &&
					c.height > 0,
			) || null
		);
	}

	// Breadth-first walk of the object graph reachable from the canvas
	// and its DOM ancestors, looking for an object matching the game
	// shape. We do not seed the walk with "window" because that would
	// pull in web-platform getters whose Promise return values surface
	// as unhandled rejections (PresentationReceiver.connectionList,
	// etc.). Thenables we do encounter are silenced and skipped.
	function findGame(canvas) {
		const SKIP = /^(parentNode|parentElement|ownerDocument|nextSibling|previousSibling|nextElementSibling|previousElementSibling|childNodes|children|firstChild|lastChild|firstElementChild|lastElementChild|host|defaultView|documentElement|body|head|window|document|top|parent|self|frames|opener|globalThis|navigator|location|history|sessionStorage|localStorage|crypto|performance|console)$/;

		const seen = new WeakSet();
		const queue = [];
		for (let el = canvas; el; el = el.parentNode) queue.push(el);

		const t0 = performance.now();
		let n = 0;
		while (queue.length && n < 150000 && performance.now() - t0 < 5000) {
			n++;
			const o = queue.shift();
			if (o == null) continue;
			const t = typeof o;
			if (t !== "object" && t !== "function") continue;
			if (seen.has(o)) continue;
			try {
				seen.add(o);
			} catch {
				continue;
			}

			if (isGame(o)) return o;

			let keys = [];
			try {
				keys = [
					...Object.getOwnPropertyNames(o),
					...Object.getOwnPropertySymbols(o),
				];
			} catch {}

			for (const k of keys) {
				if (typeof k === "string" && SKIP.test(k)) continue;
				let v;
				try {
					v = o[k];
				} catch {
					continue;
				}
				if (!v) continue;
				const vt = typeof v;
				if (vt !== "object" && vt !== "function") continue;
				if (seen.has(v)) continue;
				// Thenables carry rejections we cannot observe here; silence
				// them and skip (they do not lead to the game anyway).
				if (typeof v.then === "function") {
					try {
						Promise.resolve(v).catch(() => {});
					} catch {}
					continue;
				}
				queue.push(v);
			}
		}
		return null;
	}

	// =====================================================================
	// PHASE 1: wait until the game has finished loading
	// =====================================================================

	// Poll every 300ms until both the canvas exists and the game
	// instance behind it reports as ready. No timeout: the script
	// will keep waiting until the user starts a game.
	let game = null;
	let canvas = null;
	while (true) {
		canvas = findCanvas();
		if (canvas) {
			const candidate = findGame(canvas);
			if (isReady(candidate)) {
				game = candidate;
				break;
			}
		}
		await wait(300);
	}

	// Expose the game on window so it can be poked at from the console
	// (e.g. window.__game.cameraController.yaw).
	window.__game = game;

	// =====================================================================
	// PHASE 2: aim at each can and click it
	// =====================================================================

	const cc = game.cameraController;
	const ps = game.panoramaSphere;
	const camera = game.renderer.camera;

	// The game starts in "demo" mode where the panorama auto-rotates
	// until the first user interaction. Turn this off up front so the
	// camera does not drift between our clicks.
	game.inDemoMode = false;

	for (let i = 0; i < CANS.length; i++) {
		const can = CANS[i];

		// 1. Convert the can's UV position to a 3D direction on the
		//    cylinder using the exact same formula the game uses
		//    internally. The direction is the point in world space we
		//    want the camera (at the origin) to look at.
		const dir = ps.uvPercentToDirection(can.x, can.y);
		const f = dir.clone().normalize();

		// 2. Decompose the direction into yaw + pitch. The game uses
		//    forward = (cos(p)*sin(y), sin(p), cos(p)*cos(y)), so the
		//    inverse is yaw = atan2(x, z) and pitch = asin(y).
		const rawYaw = Math.atan2(f.x, f.z);
		const rawPitch = Math.asin(f.y);

		// 3. Compute the shortest yaw delta from the current yaw,
		//    normalised to [-pi, pi]. Without this we could spin the
		//    long way around the cylinder for a can that is only a
		//    few degrees away from the current view.
		let dY = rawYaw - cc.yaw;
		while (dY > Math.PI) dY -= 2 * Math.PI;
		while (dY < -Math.PI) dY += 2 * Math.PI;

		// 4. Snap both the target angles AND the smoothed "current"
		//    angles. The game's update loop normally lerps current
		//    toward target every frame; setting them equal bypasses
		//    the easing and makes the camera teleport instantly.
		cc.yaw = cc.yaw + dY;
		cc.pitch = Math.max(cc.minPitch, Math.min(cc.maxPitch, rawPitch));
		cc.currentYaw = cc.yaw;
		cc.currentPitch = cc.pitch;

		// 5. Manually refresh the THREE.Camera so the raycast we are
		//    about to fire sees the new orientation. The render loop
		//    would do this on the next frame, but we do it now so we
		//    do not have to wait for that frame.
		cc.updateCamera(camera);
		camera.updateMatrixWorld();

		// 6. Pitch is clamped to +/-25 degrees in 2d-image mode, but
		//    the camera's vertical FOV is 75 degrees, so cans that
		//    sit above/below the pitch limit (e.g. can-ufo at y=21.97)
		//    are still visible, just off the vertical center. Project
		//    the leftover pitch onto canvas pixels via
		//    NDC_y = tan(pitchOffset) / tan(FOV/2) so the click lands
		//    on the can plane, not above/below it.
		const pitchOffset = rawPitch - cc.pitch;
		const ndcY = Math.tan(pitchOffset) / Math.tan(FOV_V / 2);
		const r = canvas.getBoundingClientRect();
		const xPx = r.left + r.width / 2;
		const yPx = r.top + (r.height * (1 - ndcY)) / 2;

		// 7. Queue the click. game.click(...) pushes a "click" action
		//    onto the game's pending-actions queue; the next render
		//    frame runs the same raycaster a real user click would,
		//    so the can is registered as found.
		game.click({ x: xPx, y: yPx });

		// Sleep before the next iteration. Movement above was instant,
		// so this is the entire visible gap between clicks.
		await wait(DELAY_MS);
	}
})();
