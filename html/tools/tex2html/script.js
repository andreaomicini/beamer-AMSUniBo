/* the deck: head and foot lines, scaling, navigation */
(() => {
	const deck = document.querySelector('.deck');
	const frames = [...deck.querySelectorAll('.frame')];
	const d = deck.dataset;
	let n = 0;
	frames.forEach((f, i) => {
		f.setAttribute('aria-label', `${i + 1} / ${frames.length}`);
		const head = document.createElement('div');
		head.className = 'headline';
		head.innerHTML = '<div class="section"></div><div class="subsection"></div>';
		head.firstChild.textContent = f.dataset.section;
		if (f.dataset.subsection) head.lastChild.textContent = f.dataset.subsection;
		const foot = document.createElement('div');
		foot.className = 'footline';
		foot.innerHTML = '<div class="author"></div><div class="title"></div><div class="date"></div>';
		// infolines' ~~ as two spaces kept as they are: Latin Modern's no-break space is wider than its
		// space, and Firefox draws it where WebKit does not
		foot.children[0].style.whiteSpace = 'pre';
		foot.children[0].textContent = `${d.shortauthor}  (${d.shortinstitute})`;
		foot.children[1].textContent = d.shorttitle;
		foot.children[2].textContent = d.shortdate;
		const number = document.createElement('span');
		number.className = 'number';
		if (!f.hasAttribute('data-noframenumbering')) number.textContent = `${i + 1} / ${d.totalframes}`;
		foot.children[2].append(number);
		f.prepend(head);
		f.append(foot);
	});
	const fit = () => deck.style.setProperty('--scale',
		Math.min(innerWidth / +deck.dataset.width, innerHeight / +deck.dataset.height));
	const show = (i, push) => {
		n = Math.max(0, Math.min(frames.length - 1, i));
		frames.forEach((f, j) => f.classList.toggle('current', j === n));
		if (location.hash !== `#${n + 1}`) history[push ? 'pushState' : 'replaceState'](null, '', `#${n + 1}`);
	};
	const fromHash = () => {
		const h = decodeURIComponent(location.hash.slice(1));
		if (/^\d+$/.test(h)) return show(h - 1);
		const target = h && document.getElementById(h);
		show(target ? frames.findIndex(f => f.contains(target)) : n);
	};
	new ResizeObserver(fit).observe(document.documentElement);
	addEventListener('hashchange', fromHash);
	addEventListener('keydown', e => {
		if (e.metaKey || e.ctrlKey || e.altKey) return;
		if (['ArrowRight', 'ArrowDown', 'PageDown', ' ', 'Enter'].includes(e.key)) show(n + 1, true);
		else if (['ArrowLeft', 'ArrowUp', 'PageUp', 'Backspace'].includes(e.key)) show(n - 1, true);
		else if (e.key === 'Home') show(0, true);
		else if (e.key === 'End') show(frames.length - 1, true);
		else if (e.key === 'f') document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen();
		else return;
		e.preventDefault();
	});
	let x0 = null;
	addEventListener('touchstart', e => { x0 = e.touches[0].clientX; }, { passive: true });
	addEventListener('touchend', e => {
		if (x0 === null) return;
		const dx = e.changedTouches[0].clientX - x0;
		if (Math.abs(dx) > 40) show(n + (dx < 0 ? 1 : -1), true);
		x0 = null;
	});
	fit();
	fromHash();
	/* embedded: tell the host page the shape of the slides */
	if (window.parent !== window)
		window.parent.postMessage({ type: 'deck-size',
			width: +deck.dataset.width, height: +deck.dataset.height }, '*');
})();
