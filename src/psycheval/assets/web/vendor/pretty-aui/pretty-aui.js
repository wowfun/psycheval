globalThis.__zod_globalConfig ??= {}, globalThis.__zod_globalConfig.jitless = !0;
import { C as e, G as t, K as n, S as r, U as i, W as a, _ as o, a as s, c, d as l, f as u, g as d, h as f, i as p, l as m, m as h, n as g, o as _, p as v, q as y, r as b, s as x, t as S, u as ee, w as C, x as w } from "./chunks/types.js";
//#region node_modules/.pnpm/preact@10.29.8/node_modules/preact/dist/preact.module.js
var T, E, te, ne, re, ie, ae, oe, se, ce, le, ue, de, D, fe, pe = {}, me = [], he = /acit|ex(?:s|g|n|p|$)|rph|grid|ows|mnc|ntw|ine[ch]|zoo|^ord|itera/i, ge = Array.isArray;
function _e(e, t) {
	for (var n in t) e[n] = t[n];
	return e;
}
function ve(e) {
	e && e.parentNode && e.parentNode.removeChild(e);
}
function ye(e, t, n) {
	var r, i, a, o = {};
	for (a in t) a == "key" ? r = t[a] : a == "ref" ? i = t[a] : o[a] = t[a];
	if (arguments.length > 2 && (o.children = arguments.length > 3 ? T.call(arguments, 2) : n), typeof e == "function" && e.defaultProps != null) for (a in e.defaultProps) o[a] === void 0 && (o[a] = e.defaultProps[a]);
	return be(e, o, r, i, null);
}
function be(e, t, n, r, i) {
	var a = {
		type: e,
		props: t,
		key: n,
		ref: r,
		__k: null,
		__: null,
		__b: 0,
		__e: null,
		__c: null,
		constructor: void 0,
		__v: i ?? ++te,
		__i: -1,
		__u: 0
	};
	return i == null && E.vnode != null && E.vnode(a), a;
}
function O(e) {
	return e.children;
}
function k(e, t) {
	this.props = e, this.context = t;
}
function A(e, t) {
	if (t == null) return e.__ ? A(e.__, e.__i + 1) : null;
	for (var n; t < e.__k.length; t++) if ((n = e.__k[t]) != null && n.__e != null) return n.__e;
	return typeof e.type == "function" ? A(e) : null;
}
function xe(e) {
	if (e.__P && e.__d) {
		var t = e.__v, n = t.__e, r = [], i = [], a = _e({}, t);
		a.__v = t.__v + 1, E.vnode && E.vnode(a), Me(e.__P, a, t, e.__n, e.__P.namespaceURI, 32 & t.__u ? [n] : null, r, n ?? A(t), !!(32 & t.__u), i), a.__v = t.__v, a.__.__k[a.__i] = a, Pe(r, a, i), t.__e = t.__ = null, a.__e != n && j(a);
	}
}
function j(e) {
	if ((e = e.__) != null && e.__c != null) return e.__e = e.__c.base = null, e.__k.some(function(t) {
		if (t != null && t.__e != null) return e.__e = e.__c.base = t.__e;
	}), j(e);
}
function Se(e) {
	(!e.__d && (e.__d = !0) && ne.push(e) && !Ce.__r++ || re != E.debounceRendering) && ((re = E.debounceRendering) || ie)(Ce);
}
function Ce() {
	try {
		for (var e, t = 1; ne.length;) ne.length > t && ne.sort(ae), e = ne.shift(), t = ne.length, xe(e);
	} finally {
		ne.length = Ce.__r = 0;
	}
}
function we(e, t, n, r, i, a, o, s, c, l, u) {
	var d, f, p, m, h, g, _ = r && r.__k || me, v = t.length;
	for (c = Te(n, t, _, c, v), d = 0; d < v; d++) (p = n.__k[d]) != null && (f = p.__i != -1 && _[p.__i] || pe, p.__i = d, g = Me(e, p, f, i, a, o, s, c, l, u), m = p.__e, p.ref && f.ref != p.ref && (f.ref && Le(f.ref, null, p), u.push(p.ref, p.__c || m, p)), h == null && m != null && (h = m), 4 & p.__u ? (c = Ee(p, c, e), f.__e && (f.__e = null)) : typeof p.type == "function" && g !== void 0 ? c = g : m && (c = m.nextSibling), p.__u &= -7);
	return n.__e = h, c;
}
function Te(e, t, n, r, i) {
	var a, o, s, c, l, u = n.length, d = u, f = 0;
	for (e.__k = Array(i), a = 0; a < i; a++) (o = t[a]) != null && typeof o != "boolean" && typeof o != "function" ? (typeof o == "string" || typeof o == "number" || typeof o == "bigint" || o.constructor == String ? o = e.__k[a] = be(null, o, null, null, null) : ge(o) ? o = e.__k[a] = be(O, { children: o }, null, null, null) : o.constructor === void 0 && o.__b > 0 ? o = e.__k[a] = be(o.type, o.props, o.key, o.ref ? o.ref : null, o.__v) : e.__k[a] = o, c = a + f, o.__ = e, o.__b = e.__b + 1, s = null, (l = o.__i = Oe(o, n, c, d)) != -1 && (d--, (s = n[l]) && (s.__u |= 2)), s == null || s.__v == null ? (l == -1 && (i > u ? f-- : i < u && f++), typeof o.type != "function" && (o.__u |= 4)) : l != c && (l == c - 1 ? f-- : l == c + 1 ? f++ : (l > c ? f-- : f++, o.__u |= 4))) : e.__k[a] = null;
	if (d) for (a = 0; a < u; a++) (s = n[a]) != null && !(2 & s.__u) && (s.__e == r && (r = A(s)), Re(s, s));
	return r;
}
function Ee(e, t, n) {
	var r, i;
	if (typeof e.type == "function") {
		for (r = e.__k, i = 0; r && i < r.length; i++) r[i] && (r[i].__ = e, t = Ee(r[i], t, n));
		return t;
	}
	e.__e != t && (t && e.type && !t.parentNode && (t = A(e)), t = n.insertBefore(e.__e, t || null));
	do
		t &&= t.nextSibling;
	while (t != null && t.nodeType == 8);
	return t;
}
function De(e, t) {
	return t ||= [], e == null || typeof e == "boolean" || (ge(e) ? e.some(function(e) {
		De(e, t);
	}) : t.push(e)), t;
}
function Oe(e, t, n, r) {
	var i, a, o, s = e.key, c = e.type, l = t[n], u = l != null && !(2 & l.__u);
	if (l === null && s == null || u && s == l.key && c == l.type) return n;
	if (r > +!!u) {
		for (i = n - 1, a = n + 1; i >= 0 || a < t.length;) if ((l = t[o = i >= 0 ? i-- : a++]) != null && !(2 & l.__u) && s == l.key && c == l.type) return o;
	}
	return -1;
}
function ke(e, t, n) {
	t[0] == "-" ? e.setProperty(t, n ?? "") : e[t] = n == null ? "" : typeof n != "number" || he.test(t) ? n : n + "px";
}
function Ae(e, t, n, r, i) {
	var a, o;
	n: if (t == "style") {
		if (typeof n == "string") e.style.cssText = n;
		else {
			if (typeof r == "string" && (e.style.cssText = r = ""), r) for (t in r) n && t in n || ke(e.style, t, "");
			if (n) for (t in n) r && n[t] == r[t] || ke(e.style, t, n[t]);
		}
	} else if (t[0] == "o" && t[1] == "n") a = t != (t = t.replace(le, "$1")), o = t.toLowerCase(), t = o in e || t == "onFocusOut" || t == "onFocusIn" ? o.slice(2) : t.slice(2), e.l ||= {}, e.l[t + a] = n, n ? r ? n[ce] = r[ce] : (n[ce] = ue, e.addEventListener(t, a ? D : de, a)) : e.removeEventListener(t, a ? D : de, a);
	else {
		if (i == "http://www.w3.org/2000/svg") t = t.replace(/xlink(H|:h)/, "h").replace(/sName$/, "s");
		else if (t != "width" && t != "height" && t != "href" && t != "list" && t != "form" && t != "tabIndex" && t != "download" && t != "rowSpan" && t != "colSpan" && t != "role" && t != "popover" && t in e) try {
			e[t] = n ?? "";
			break n;
		} catch {}
		typeof n == "function" || (n == null || !1 === n && t[4] != "-" ? e.removeAttribute(t) : e.setAttribute(t, t == "popover" && n == 1 ? "" : n));
	}
}
function je(e) {
	return function(t) {
		if (this.l) {
			var n = this.l[t.type + e];
			if (t[se] == null) t[se] = ue++;
			else if (t[se] < n[ce]) return;
			return n(E.event ? E.event(t) : t);
		}
	};
}
function Me(e, t, n, r, i, a, o, s, c, l) {
	var u, d, f, p, m, h, g, _, v, y, b, x, S, ee, C, w, T = t.type;
	if (t.constructor !== void 0) return null;
	128 & n.__u && (c = !!(32 & n.__u), a = [s = t.__e = n.__e]), (u = E.__b) && u(t);
	n: if (typeof T == "function") {
		d = o.length;
		try {
			if (v = t.props, y = T.prototype && T.prototype.render, b = (u = T.contextType) && r[u.__c], x = u ? b ? b.props.value : u.__ : r, n.__c ? _ = (f = t.__c = n.__c).__ = f.__E : (y ? t.__c = f = new T(v, x) : (t.__c = f = new k(v, x), f.constructor = T, f.render = ze), b && b.sub(f), f.state || (f.state = {}), f.__n = r, p = f.__d = !0, f.__h = [], f._sb = []), y && f.__s == null && (f.__s = f.state), y && T.getDerivedStateFromProps != null && (f.__s == f.state && (f.__s = _e({}, f.__s)), _e(f.__s, T.getDerivedStateFromProps(v, f.__s))), m = f.props, h = f.state, f.__v = t, p) y && T.getDerivedStateFromProps == null && f.componentWillMount != null && f.componentWillMount(), y && f.componentDidMount != null && f.__h.push(f.componentDidMount);
			else {
				if (y && T.getDerivedStateFromProps == null && v !== m && f.componentWillReceiveProps != null && f.componentWillReceiveProps(v, x), t.__v == n.__v || !f.__e && f.shouldComponentUpdate != null && !1 === f.shouldComponentUpdate(v, f.__s, x)) {
					t.__v != n.__v && (f.props = v, f.state = f.__s, f.__d = !1), t.__e = n.__e, t.__k = n.__k, t.__k.some(function(e) {
						e && (e.__ = t);
					}), me.push.apply(f.__h, f._sb), f._sb = [], f.__h.length && o.push(f), s = A(n);
					break n;
				}
				f.componentWillUpdate != null && f.componentWillUpdate(v, f.__s, x), y && f.componentDidUpdate != null && f.__h.push(function() {
					f.componentDidUpdate(m, h, g);
				});
			}
			if (f.context = x, f.props = v, f.__P = e, f.__e = !1, S = E.__r, ee = 0, y) f.state = f.__s, f.__d = !1, S && S(t), u = f.render(f.props, f.state, f.context), me.push.apply(f.__h, f._sb), f._sb = [];
			else do
				f.__d = !1, S && S(t), u = f.render(f.props, f.state, f.context), f.state = f.__s;
			while (f.__d && ++ee < 25);
			f.state = f.__s, f.getChildContext != null && (r = _e(_e({}, r), f.getChildContext())), y && !p && f.getSnapshotBeforeUpdate != null && (g = f.getSnapshotBeforeUpdate(m, h)), C = u != null && u.type === O && u.key == null ? Fe(u.props.children) : u, s = we(e, ge(C) ? C : [C], t, n, r, i, a, o, s, c, l), f.base = t.__e, t.__u &= -161, f.__h.length && o.push(f), _ && (f.__E = f.__ = null);
		} catch (e) {
			if (o.length = d, t.__v = null, c || a != null) {
				if (e.then) {
					for (t.__u |= c ? 160 : 128; s && s.nodeType == 8 && s.nextSibling;) s = s.nextSibling;
					a != null && (a[a.indexOf(s)] = null), t.__e = s;
				} else if (a != null) for (w = a.length; w--;) ve(a[w]);
			} else t.__e = n.__e;
			t.__k ??= n.__k || [], e.then || Ne(t), E.__e(e, t, n);
		}
	} else a == null && t.__v == n.__v ? (t.__k = n.__k, t.__e = n.__e) : s = t.__e = Ie(n.__e, t, n, r, i, a, o, c, l);
	return (u = E.diffed) && u(t), 128 & t.__u ? void 0 : s;
}
function Ne(e) {
	e && (e.__c && (e.__c.__e = !0), e.__k && e.__k.some(Ne));
}
function Pe(e, t, n) {
	for (var r = 0; r < n.length; r++) Le(n[r], n[++r], n[++r]);
	E.__c && E.__c(t, e), e.some(function(t) {
		try {
			e = t.__h, t.__h = [], e.some(function(e) {
				e.call(t);
			});
		} catch (e) {
			E.__e(e, t.__v);
		}
	});
}
function Fe(e) {
	return typeof e != "object" || !e || e.__b > 0 ? e : ge(e) ? e.map(Fe) : e.constructor === void 0 ? _e({}, e) : null;
}
function Ie(e, t, n, r, i, a, o, s, c) {
	var l, u, d, f, p, m, h, g = n.props || pe, _ = t.props, v = t.type;
	if (v == "svg" ? i = "http://www.w3.org/2000/svg" : v == "math" ? i = "http://www.w3.org/1998/Math/MathML" : i ||= "http://www.w3.org/1999/xhtml", a != null) {
		for (l = 0; l < a.length; l++) if ((p = a[l]) && "setAttribute" in p == !!v && (v ? p.localName == v : p.nodeType == 3)) {
			e = p, a[l] = null;
			break;
		}
	}
	if (e == null) {
		if (v == null) return document.createTextNode(_);
		e = document.createElementNS(i, v, _.is && _), s &&= (E.__m && E.__m(t, a), !1), a = null;
	}
	if (v == null) g === _ || s && e.data == _ || (e.data = _);
	else {
		if (a = v == "textarea" && _.defaultValue != null ? null : a && T.call(e.childNodes), !s && a != null) for (g = {}, l = 0; l < e.attributes.length; l++) g[(p = e.attributes[l]).name] = p.value;
		for (l in g) p = g[l], l == "dangerouslySetInnerHTML" ? d = p : l == "children" || l in _ || l == "value" && "defaultValue" in _ || l == "checked" && "defaultChecked" in _ || Ae(e, l, null, p, i);
		for (l in _) p = _[l], l == "children" ? f = p : l == "dangerouslySetInnerHTML" ? u = p : l == "value" ? m = p : l == "checked" ? h = p : s && typeof p != "function" || g[l] === p || Ae(e, l, p, g[l], i);
		if (u) s || d && (u.__html == d.__html || u.__html == e.innerHTML) || (e.innerHTML = u.__html), t.__k = [];
		else if (d && (e.innerHTML = ""), we(t.type == "template" ? e.content : e, ge(f) ? f : [f], t, n, r, v == "foreignObject" ? "http://www.w3.org/1999/xhtml" : i, a, o, a ? a[0] : n.__k && A(n, 0), s, c), a != null) for (l = a.length; l--;) ve(a[l]);
		s && v != "textarea" || (l = "value", v == "progress" && m == null ? e.removeAttribute("value") : m != null && (m !== e[l] || v == "progress" && !m || v == "option" && m != g[l]) && Ae(e, l, m, g[l], i), l = "checked", h != null && h != e[l] && Ae(e, l, h, g[l], i));
	}
	return e;
}
function Le(e, t, n) {
	try {
		if (typeof e == "function") {
			var r = typeof e.__u == "function";
			r && e.__u(), r && t == null || (e.__u = e(t));
		} else e.current = t;
	} catch (e) {
		E.__e(e, n);
	}
}
function Re(e, t, n) {
	var r, i;
	if (E.unmount && E.unmount(e), (r = e.ref) && (r.current && r.current != e.__e || Le(r, null, t)), (r = e.__c) != null) {
		if (r.componentWillUnmount) try {
			r.componentWillUnmount();
		} catch (e) {
			E.__e(e, t);
		}
		r.base = r.__P = r.__n = null;
	}
	if (r = e.__k) for (i = 0; i < r.length; i++) r[i] && Re(r[i], t, n || typeof e.type != "function");
	n || ve(e.__e), e.__c = e.__ = e.__e = void 0;
}
function ze(e, t, n) {
	return this.constructor(e, n);
}
function Be(e, t, n) {
	var r, i, a, o;
	t == document && (t = document.documentElement), E.__ && E.__(e, t), i = (r = typeof n == "function") ? null : n && n.__k || t.__k, a = [], o = [], Me(t, e = (!r && n || t).__k = ye(O, null, [e]), i || pe, pe, t.namespaceURI, !r && n ? [n] : i ? null : t.firstChild ? T.call(t.childNodes) : null, a, !r && n ? n : i ? i.__e : t.firstChild, r, o), Pe(a, e, o), e.props.children = null;
}
function Ve(e) {
	function t(e) {
		var n, r;
		return this.getChildContext || (n = /* @__PURE__ */ new Set(), (r = {})[t.__c] = this, this.getChildContext = function() {
			return r;
		}, this.componentWillUnmount = function() {
			n = null;
		}, this.shouldComponentUpdate = function(e) {
			this.props.value != e.value && n.forEach(function(e) {
				e.__e = !0, Se(e);
			});
		}, this.sub = function(e) {
			n.add(e);
			var t = e.componentWillUnmount;
			e.componentWillUnmount = function() {
				n && n.delete(e), t && t.call(e);
			};
		}), e.children;
	}
	return t.__c = "__cC" + fe++, t.__ = e, t.Provider = t.__l = (t.Consumer = function(e, t) {
		return e.children(t);
	}).contextType = t, t;
}
T = me.slice, E = { __e: function(e, t, n, r) {
	for (var i, a, o; t = t.__;) if ((i = t.__c) && !i.__) try {
		if ((a = i.constructor) && a.getDerivedStateFromError != null && (i.setState(a.getDerivedStateFromError(e)), o = i.__d), i.componentDidCatch != null && (i.componentDidCatch(e, r || {}), o = i.__d), o) return i.__E = i;
	} catch (t) {
		e = t;
	}
	throw e;
} }, te = 0, k.prototype.setState = function(e, t) {
	var n = this.__s != null && this.__s != this.state ? this.__s : this.__s = _e({}, this.state);
	typeof e == "function" && (e = e(_e({}, n), this.props)), e && _e(n, e), e != null && this.__v && (t && this._sb.push(t), Se(this));
}, k.prototype.forceUpdate = function(e) {
	this.__v && (this.__e = !0, e && this.__h.push(e), Se(this));
}, k.prototype.render = O, ne = [], ie = typeof Promise == "function" ? Promise.prototype.then.bind(Promise.resolve()) : setTimeout, ae = function(e, t) {
	return e.__v.__b - t.__v.__b;
}, Ce.__r = 0, oe = Math.random().toString(8), se = "__d" + oe, ce = "__a" + oe, le = /(PointerCapture)$|Capture$/i, ue = 0, de = je(!1), D = je(!0), fe = 0;
//#endregion
//#region node_modules/.pnpm/preact@10.29.8/node_modules/preact/hooks/dist/hooks.module.js
var He, M, Ue, We, Ge = 0, Ke = [], N = E, qe = N.__b, Je = N.__r, Ye = N.diffed, Xe = N.__c, P = N.unmount, Ze = N.__;
function Qe(e, t) {
	N.__h && N.__h(M, e, Ge || t), Ge = 0;
	var n = M.__H || (M.__H = {
		__: [],
		__h: []
	});
	return e >= n.__.length && n.__.push({}), n.__[e];
}
function F(e) {
	return Ge = 1, $e(ut, e);
}
function $e(e, t, n) {
	var r = Qe(He++, 2);
	if (r.t = e, !r.__c && (r.__ = [n ? n(t) : ut(void 0, t), function(e) {
		var t = r.__N ? r.__N[0] : r.__[0], n = r.t(t, e);
		t !== n && (r.__N = [n, r.__[1]], r.__c.setState({}));
	}], r.__c = M, !M.__f)) {
		var i = function(e, t, n) {
			if (!r.__c.__H) return !0;
			var i = !1, o = r.__c.props !== e;
			if (r.__c.__H.__.some(function(e) {
				if (e.__N) {
					i = !0;
					var t = e.__[0];
					e.__ = e.__N, e.__N = void 0, t !== e.__[0] && (o = !0);
				}
			}), a) {
				var s = a.call(this, e, t, n);
				return i ? s || o : s;
			}
			return !i || o;
		};
		M.__f = !0;
		var a = M.shouldComponentUpdate, o = M.componentWillUpdate;
		M.componentWillUpdate = function(e, t, n) {
			if (this.__e) {
				var r = a;
				a = void 0, i(e, t, n), a = r;
			}
			o && o.call(this, e, t, n);
		}, M.shouldComponentUpdate = i;
	}
	return r.__N || r.__;
}
function I(e, t) {
	var n = Qe(He++, 3);
	!N.__s && lt(n.__H, t) && (n.__ = e, n.u = t, M.__H.__h.push(n));
}
function et(e, t) {
	var n = Qe(He++, 4);
	!N.__s && lt(n.__H, t) && (n.__ = e, n.u = t, M.__h.push(n));
}
function L(e) {
	return Ge = 5, tt(function() {
		return { current: e };
	}, []);
}
function tt(e, t) {
	var n = Qe(He++, 7);
	return lt(n.__H, t) && (n.__ = e(), n.__H = t, n.__h = e), n.__;
}
function nt(e, t) {
	return Ge = 8, tt(function() {
		return e;
	}, t);
}
function rt(e) {
	var t = M.context[e.__c], n = Qe(He++, 9);
	return n.c = e, t ? (n.__ ?? (n.__ = !0, t.sub(M)), t.props.value) : e.__;
}
function it() {
	var e = Qe(He++, 11);
	if (!e.__) {
		for (var t = M.__v; t !== null && !t.__m && t.__ !== null;) t = t.__;
		var n = t.__m || (t.__m = [0, 0]);
		e.__ = "P" + n[0] + "-" + n[1]++;
	}
	return e.__;
}
function R() {
	for (var e; e = Ke.shift();) {
		var t = e.__H;
		if (e.__P && t) try {
			t.__h.some(st), t.__h.some(ct), t.__h = [];
		} catch (n) {
			t.__h = [], N.__e(n, e.__v);
		}
	}
}
N.__b = function(e) {
	M = null, qe && qe(e);
}, N.__ = function(e, t) {
	e && t.__k && t.__k.__m && (e.__m = t.__k.__m), Ze && Ze(e, t);
}, N.__r = function(e) {
	Je && Je(e), He = 0;
	var t = (M = e.__c).__H;
	t && (Ue === M ? (t.__h = [], M.__h = [], t.__.some(function(e) {
		e.__N && (e.__ = e.__N), e.u = e.__N = void 0;
	})) : (t.__h.some(st), t.__h.some(ct), t.__h = [], He = 0)), Ue = M;
}, N.diffed = function(e) {
	Ye && Ye(e);
	var t = e.__c;
	t && t.__H && (t.__H.__h.length && (Ke.push(t) !== 1 && We === N.requestAnimationFrame || ((We = N.requestAnimationFrame) || ot)(R)), t.__H.__.some(function(e) {
		e.u &&= (e.__H = e.u, void 0);
	})), Ue = M = null;
}, N.__c = function(e, t) {
	t.some(function(e) {
		try {
			e.__h.some(st), e.__h = e.__h.filter(function(e) {
				return !e.__ || ct(e);
			});
		} catch (n) {
			t.some(function(e) {
				e.__h &&= [];
			}), t = [], N.__e(n, e.__v);
		}
	}), Xe && Xe(e, t);
}, N.unmount = function(e) {
	P && P(e);
	var t, n = e.__c;
	n && n.__H && (n.__H.__.some(function(e) {
		try {
			st(e);
		} catch (e) {
			t = e;
		}
	}), n.__H = void 0, t && N.__e(t, n.__v));
};
var at = typeof requestAnimationFrame == "function";
function ot(e) {
	var t, n = function() {
		clearTimeout(r), at && cancelAnimationFrame(t), setTimeout(e);
	}, r = setTimeout(n, 35);
	at && (t = requestAnimationFrame(n));
}
function st(e) {
	var t = M, n = e.__c;
	typeof n == "function" && (e.__c = void 0, n()), M = t;
}
function ct(e) {
	var t = M;
	e.__c = e.__(), M = t;
}
function lt(e, t) {
	return !e || e.length !== t.length || t.some(function(t, n) {
		return t !== e[n];
	});
}
function ut(e, t) {
	return typeof t == "function" ? t(e) : t;
}
//#endregion
//#region node_modules/.pnpm/preact@10.29.8/node_modules/preact/compat/dist/compat.module.js
function dt(e, t) {
	for (var n in t) e[n] = t[n];
	return e;
}
function ft(e, t) {
	for (var n in e) if (n !== "__source" && !(n in t)) return !0;
	for (var r in t) if (r !== "__source" && e[r] !== t[r]) return !0;
	return !1;
}
function pt(e, t) {
	var n = t(), r = F({ t: {
		__: n,
		u: t
	} }), i = r[0].t, a = r[1];
	return et(function() {
		i.__ = n, i.u = t, mt(i) && a({ t: i });
	}, [
		e,
		n,
		t
	]), I(function() {
		return mt(i) && a({ t: i }), e(function() {
			mt(i) && a({ t: i });
		});
	}, [e]), n;
}
function mt(e) {
	try {
		return !((t = e.__) === (n = e.u()) && (t !== 0 || 1 / t == 1 / n) || t != t && n != n);
	} catch {
		return !0;
	}
	var t, n;
}
function ht(e, t) {
	this.props = e, this.context = t;
}
function gt(e, t) {
	function n(e) {
		var n = this.props.ref;
		return n != e.ref && n && (typeof n == "function" ? n(null) : n.current = null), t ? !t(this.props, e) || n != e.ref : ft(this.props, e);
	}
	function r(t) {
		return this.shouldComponentUpdate = n, ye(e, t);
	}
	return r.displayName = "Memo(" + (e.displayName || e.name) + ")", r.__f = r.prototype.isReactComponent = !0, r.type = e, r;
}
(ht.prototype = new k()).isPureReactComponent = !0, ht.prototype.shouldComponentUpdate = function(e, t) {
	return ft(this.props, e) || ft(this.state, t);
};
var _t = E.__b;
E.__b = function(e) {
	e.type && e.type.__f && e.ref && (e.props.ref = e.ref, e.ref = null), _t && _t(e);
}, typeof Symbol < "u" && Symbol.for;
var vt = E.__e;
E.__e = function(e, t, n, r) {
	if (e.then) {
		for (var i, a = t; a = a.__;) if ((i = a.__c) && i.__c) return t.__e ?? (t.__e = n.__e, t.__k = n.__k || []), i.__c(e, t);
	}
	vt(e, t, n, r);
};
var yt = E.unmount;
function bt(e, t, n) {
	return e && (e.__c && e.__c.__H && (e.__c.__H.__.forEach(function(e) {
		typeof e.__c == "function" && e.__c();
	}), e.__c.__H = null), (e = dt({}, e)).__c != null && (e.__c.__P === n && (e.__c.__P = t), e.__c.__e = !0, e.__c = null), e.__k = e.__k && e.__k.map(function(e) {
		return bt(e, t, n);
	})), e;
}
function xt(e, t, n) {
	return e && n && (e.__v = null, e.__k = e.__k && e.__k.map(function(e) {
		return xt(e, t, n);
	}), e.__c && e.__c.__P === t && (e.__e && n.appendChild(e.__e), e.__c.__e = !0, e.__c.__P = n)), e;
}
function St() {
	this.__u = 0, this.o = null, this.__b = null;
}
function Ct(e) {
	var t = e.__ && e.__.__c;
	return t && t.__a && t.__a(e);
}
function wt() {
	this.i = null, this.l = null;
}
E.unmount = function(e) {
	var t = e.__c;
	t && (t.__z = !0), t && t.__R && t.__R(), t && 32 & e.__u && (e.type = null), yt && yt(e);
}, (St.prototype = new k()).__c = function(e, t) {
	var n = t.__c, r = this;
	r.o ??= [], r.o.push(n);
	var i = Ct(r.__v), a = !1, o = function() {
		a || r.__z || (a = !0, n.__R = null, i ? i(c) : c());
	};
	n.__R = o;
	var s = n.__P;
	n.__P = null;
	var c = function() {
		if (!--r.__u) {
			if (r.state.__a) {
				var e = r.state.__a;
				r.__v.__k[0] = xt(e, e.__c.__P, e.__c.__O);
			}
			var t;
			for (r.setState({ __a: r.__b = null }); t = r.o.pop();) t.__P = s, t.forceUpdate();
		}
	};
	r.__u++ || 32 & t.__u || r.setState({ __a: r.__b = r.__v.__k[0] }), e.then(o, o);
}, St.prototype.componentWillUnmount = function() {
	this.o = [];
}, St.prototype.render = function(e, t) {
	if (this.__b) {
		if (this.__v.__k) {
			var n = document.createElement("div"), r = this.__v.__k[0].__c;
			this.__v.__k[0] = bt(this.__b, n, r.__O = r.__P);
		}
		this.__b = null;
	}
	var i = t.__a && ye(O, null, e.fallback);
	return i && (i.__u &= -33), [ye(O, null, t.__a ? null : e.children), i];
};
var Tt = function(e, t, n) {
	if (++n[1] === n[0] && e.l.delete(t), e.props.revealOrder && (e.props.revealOrder[0] !== "t" || !e.l.size)) for (n = e.i; n;) {
		for (; n.length > 3;) n.pop()();
		if (n[1] < n[0]) break;
		e.i = n = n[2];
	}
};
(wt.prototype = new k()).__a = function(e) {
	var t = this, n = Ct(t.__v), r = t.l.get(e);
	return r[0]++, function(i) {
		var a = function() {
			t.props.revealOrder ? (r.push(i), Tt(t, e, r)) : i();
		};
		n ? n(a) : a();
	};
}, wt.prototype.render = function(e) {
	this.i = null, this.l = /* @__PURE__ */ new Map();
	var t = De(e.children);
	e.revealOrder && e.revealOrder[0] === "b" && t.reverse();
	for (var n = t.length; n--;) this.l.set(t[n], this.i = [
		1,
		0,
		this.i
	]);
	return e.children;
}, wt.prototype.componentDidUpdate = wt.prototype.componentDidMount = function() {
	var e = this;
	this.l.forEach(function(t, n) {
		Tt(e, n, t);
	});
};
var Et = typeof Symbol < "u" && Symbol.for && Symbol.for("react.element") || 60103, Dt = /^(?:accent|alignment|arabic|baseline|cap|clip(?!PathU)|color|dominant|fill|flood|font|glyph(?!R)|horiz|image(!S)|letter|lighting|marker(?!H|W|U)|overline|paint|pointer|shape|stop|strikethrough|stroke|text(?!L)|transform|underline|unicode|units|v|vector|vert|word|writing|x(?!C))[A-Z]/, Ot = /^on(Ani|Tra|Tou|BeforeInp|Compo)/, kt = /[A-Z0-9]/g, At = typeof document < "u", jt = function(e) {
	return (typeof Symbol < "u" && typeof Symbol() == "symbol" ? /fil|che|rad/ : /fil|che|ra/).test(e);
};
function Mt(e, t, n) {
	return t.__k ?? (t.textContent = ""), Be(e, t), typeof n == "function" && n(), e ? e.__c : null;
}
k.prototype.isReactComponent = !0, [
	"componentWillMount",
	"componentWillReceiveProps",
	"componentWillUpdate"
].forEach(function(e) {
	Object.defineProperty(k.prototype, e, {
		configurable: !0,
		get: function() {
			return this["UNSAFE_" + e];
		},
		set: function(t) {
			Object.defineProperty(this, e, {
				configurable: !0,
				writable: !0,
				value: t
			});
		}
	});
});
var Nt = E.event;
E.event = function(e) {
	return Nt && (e = Nt(e)), e.persist = function() {}, e.isPropagationStopped = function() {
		return this.cancelBubble;
	}, e.isDefaultPrevented = function() {
		return this.defaultPrevented;
	}, e.nativeEvent = e;
};
var Pt = {
	configurable: !0,
	get: function() {
		return this.class;
	}
}, Ft = E.vnode;
E.vnode = function(e) {
	typeof e.type == "string" && function(e) {
		var t = e.props, n = e.type, r = {}, i = n.indexOf("-") == -1;
		for (var a in t) {
			var o = t[a];
			if (!(a === "value" && "defaultValue" in t && o == null || At && a === "children" && n === "noscript" || a === "class" || a === "className")) {
				var s = a.toLowerCase();
				a === "defaultValue" && "value" in t && t.value == null ? a = "value" : a === "download" && !0 === o ? o = "" : s === "translate" && o === "no" ? o = !1 : s[0] === "o" && s[1] === "n" ? s === "ondoubleclick" ? a = "ondblclick" : s !== "onchange" || n !== "input" && n !== "textarea" || jt(t.type) ? s === "onfocus" ? a = "onfocusin" : s === "onblur" ? a = "onfocusout" : Ot.test(a) && (a = s) : s = a = "oninput" : i && Dt.test(a) ? a = a.replace(kt, "-$&").toLowerCase() : o === null && (o = void 0), s === "oninput" && r[a = s] && (a = "oninputCapture"), r[a] = o;
			}
		}
		n == "select" && (r.multiple && Array.isArray(r.value) && (r.value = De(t.children).forEach(function(e) {
			e.props.selected = r.value.indexOf(e.props.value) != -1;
		})), r.defaultValue != null && (r.value = De(t.children).forEach(function(e) {
			e.props.selected = r.multiple ? r.defaultValue.indexOf(e.props.value) != -1 : r.defaultValue == e.props.value;
		}))), t.class && !t.className ? (r.class = t.class, Object.defineProperty(r, "className", Pt)) : t.className && (r.class = r.className = t.className), e.props = r;
	}(e), e.$$typeof = Et, Ft && Ft(e);
};
var It = E.__r;
E.__r = function(e) {
	It && It(e), e.__c;
};
var Lt = E.diffed;
E.diffed = function(e) {
	Lt && Lt(e);
	var t = e.props, n = e.__e;
	n != null && e.type === "textarea" && "value" in t && t.value !== n.value && (n.value = t.value == null ? "" : t.value);
};
function Rt(e) {
	return !!e.__k && (Be(null, e), !0);
}
//#endregion
//#region node_modules/.pnpm/preact@10.29.8/node_modules/preact/compat/client.mjs
function zt(e) {
	return {
		render: function(t) {
			Mt(t, e);
		},
		unmount: function() {
			Rt(e);
		}
	};
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/line-buffer.js
var Bt = 10, Vt = class {
	#e = [];
	push(e) {
		let t = [], n = 0, r = e.indexOf(Bt, n);
		for (; r !== -1;) t.push(this.#t(e.subarray(n, r))), n = r + 1, r = e.indexOf(Bt, n);
		return n < e.byteLength && this.#e.push(n === 0 ? e : new Uint8Array(e.subarray(n))), t;
	}
	flush() {
		if (this.#e.length !== 0) return this.#t(/* @__PURE__ */ new Uint8Array());
	}
	#t(e) {
		if (this.#e.length === 0) return e;
		let t = e.byteLength;
		for (let e of this.#e) t += e.byteLength;
		let n = new Uint8Array(t), r = 0;
		for (let e of this.#e) n.set(e, r), r += e.byteLength;
		return n.set(e, r), this.#e = [], n;
	}
};
//#endregion
//#region src/core/protocol/v1.ts
async function Ht(e) {
	let { sink: t, host: r } = e, i = d({ name: e.clientInfo.name });
	i = i.onRequest(o.client.session.requestPermission, async ({ params: e }) => {
		let n = e, r = await t.onPermission(e.sessionId, qt(n), n);
		return x(r);
	}).onRequest(o.client.elicitation.create, async ({ params: e }) => {
		let n = e, r = await t.onElicitation("sessionId" in e && typeof e.sessionId == "string" ? e.sessionId : void 0, s(n), n);
		return p(r);
	}).onNotification(o.client.session.update, ({ params: e }) => {
		t.onProtocol(o.client.session.update, e), t.onUpdate(e.sessionId, e.update);
	}).onNotification(o.client.elicitation.complete, ({ params: e }) => {
		t.onProtocol(o.client.elicitation.complete, e), t.onElicitationComplete(e.elicitationId);
	});
	let a = r?.v1?.filesystem;
	a?.readTextFile && (i = i.onRequest(o.client.fs.readTextFile, async ({ params: e }) => await a.readTextFile(e))), a?.writeTextFile && (i = i.onRequest(o.client.fs.writeTextFile, async ({ params: e }) => await a.writeTextFile(e)));
	let c = r?.v1?.terminal;
	c && (i = i.onRequest(o.client.terminal.create, async ({ params: e }) => await c.create(e)).onRequest(o.client.terminal.output, async ({ params: e }) => await c.output(e)).onRequest(o.client.terminal.release, async ({ params: e }) => await c.release(e)).onRequest(o.client.terminal.waitForExit, async ({ params: e }) => await c.waitForExit(e)).onRequest(o.client.terminal.kill, async ({ params: e }) => await c.kill(e)));
	let l = i.connect(e.stream), f = !1;
	l.closed.then(() => {
		f || t.onDisconnect();
	});
	let m;
	try {
		m = await l.agent.request(o.agent.initialize, {
			protocolVersion: 1,
			clientInfo: {
				name: e.clientInfo.name,
				version: e.clientInfo.version,
				...e.clientInfo.title ? { title: e.clientInfo.title } : {}
			},
			clientCapabilities: {
				fs: {
					readTextFile: !!a?.readTextFile,
					writeTextFile: !!a?.writeTextFile
				},
				terminal: !!c,
				session: { configOptions: { boolean: {} } },
				auth: { terminal: !!r?.terminalAuth },
				elicitation: {
					form: {},
					url: {}
				}
			}
		});
	} catch (e) {
		throw l.close(e), new n("INITIALIZE_REJECTED", "ACP v1 initialization failed", {
			cause: e,
			protocol: 1,
			phase: "initialize",
			retryable: !0
		});
	}
	if (m.protocolVersion !== 1) throw l.close(), new n("PROTOCOL_VERSION_MISMATCH", `Requested ACP v1 but agent selected v${m.protocolVersion}`, {
		protocol: 1,
		phase: "initialize"
	});
	let h = m.agentCapabilities, g = h?.sessionCapabilities;
	return new Ut(l, {
		protocolVersion: 1,
		...m.agentInfo?.title || m.agentInfo?.name ? { agentName: m.agentInfo.title ?? m.agentInfo.name } : {},
		authMethods: u(m.authMethods),
		capabilities: {
			listSessions: g?.list != null,
			loadSession: h?.loadSession === !0,
			resumeSession: g?.resume != null,
			closeSession: g?.close != null,
			deleteSession: g?.delete != null
		},
		promptCapabilities: {
			image: h?.promptCapabilities?.image === !0,
			audio: h?.promptCapabilities?.audio === !0,
			embeddedContext: h?.promptCapabilities?.embeddedContext === !0
		},
		additionalDirectories: g?.additionalDirectories != null,
		mcp: {
			stdio: !0,
			http: h?.mcpCapabilities?.http === !0,
			sse: h?.mcpCapabilities?.sse === !0
		}
	}, t, r, () => {
		f = !0;
	});
}
var Ut = class {
	connection;
	initialized;
	sink;
	host;
	markClosed;
	version = 1;
	#e = /* @__PURE__ */ new Map();
	constructor(e, t, n, r, i) {
		this.connection = e, this.initialized = t, this.sink = n, this.host = r, this.markClosed = i;
	}
	async newSession(e) {
		b(e, this.initialized, 1, "session/new");
		let t = await S(() => this.connection.agent.request(o.agent.session.new, Wt(e)), 1, "session/new");
		return this.#e.set(t.sessionId, !t.configOptions?.length && !!t.modes), Kt(t.sessionId, t.configOptions, t.modes);
	}
	async openSession(e, t, r) {
		b(t, this.initialized, 1, "session/open");
		let i = {
			...Wt(t),
			sessionId: e
		};
		if (r === "all" && this.initialized.capabilities.loadSession) {
			let t = await S(() => this.connection.agent.request(o.agent.session.load, i), 1, "session/open");
			return this.#e.set(e, !t.configOptions?.length && !!t.modes), Kt(e, t.configOptions, t.modes);
		}
		if (!this.initialized.capabilities.resumeSession) throw new n("CAPABILITY_REQUIRED", "The agent cannot open existing sessions", {
			protocol: 1,
			phase: "session/resume"
		});
		let a = await S(() => this.connection.agent.request(o.agent.session.resume, i), 1, "session/open");
		return this.#e.set(e, !a.configOptions?.length && !!a.modes), Kt(e, a.configOptions, a.modes, r === "all");
	}
	async listSessions(e, t) {
		if (!this.initialized.capabilities.listSessions) throw new n("CAPABILITY_REQUIRED", "The agent does not support session/list", { protocol: 1 });
		let r = await this.connection.agent.request(o.agent.session.list, {
			cwd: e,
			...t ? { cursor: t } : {}
		});
		return f(r);
	}
	async deleteSession(e) {
		if (!this.initialized.capabilities.deleteSession) throw new n("CAPABILITY_REQUIRED", "The agent does not support session/delete", { protocol: 1 });
		await this.connection.agent.request(o.agent.session.delete, { sessionId: e }), this.#e.delete(e);
	}
	async closeSession(e) {
		if (!this.initialized.capabilities.closeSession) {
			this.#e.delete(e);
			return;
		}
		await this.connection.agent.request(o.agent.session.close, { sessionId: e }), this.#e.delete(e);
	}
	promptReady(e) {
		return !0;
	}
	async prompt(e, t, n) {
		let r = this.connection.agent.request(o.agent.session.prompt, {
			sessionId: e,
			prompt: t
		});
		return n(), (await r).stopReason;
	}
	async cancel(e) {
		await this.connection.agent.notify(o.agent.session.cancel, { sessionId: e });
	}
	async setConfigOption(e, t, n) {
		if (this.#e.get(e) && t === "mode" && typeof n == "string") return await this.connection.agent.request(o.agent.session.setMode, {
			sessionId: e,
			modeId: n
		}), [];
		let r = await this.connection.agent.request(o.agent.session.setConfigOption, {
			sessionId: e,
			configId: t,
			value: n,
			...typeof n == "boolean" ? { type: "boolean" } : {}
		});
		return v(r.configOptions);
	}
	async authenticate(e) {
		if (e.type === "terminal") {
			if (!this.host?.terminalAuth) throw new n("CAPABILITY_REQUIRED", "Terminal authentication needs a host handler", { protocol: 1 });
			await this.host.terminalAuth(e);
			return;
		}
		await this.connection.agent.request(o.agent.authenticate, { methodId: e.id });
	}
	async logout() {
		await this.connection.agent.request(o.agent.logout, {}), this.#e.clear();
	}
	async close(e) {
		this.markClosed(), this.#e.clear(), this.connection.close(e), await this.connection.closed;
	}
};
function Wt(e) {
	return {
		cwd: e.cwd,
		mcpServers: (e.mcpServers ?? []).map(Gt),
		...e.additionalDirectories?.length ? { additionalDirectories: [...e.additionalDirectories] } : {}
	};
}
function Gt(e) {
	return e.type === "stdio" ? {
		name: e.name,
		command: e.command,
		args: [...e.args ?? []],
		env: [...e.env ?? []]
	} : {
		type: e.type,
		name: e.name,
		url: e.url,
		headers: [...e.headers ?? []]
	};
}
function Kt(e, t, n, r = !1) {
	let i = v(t);
	return {
		sessionId: e,
		configOptions: i.length ? i : h(n),
		...r ? { historyGap: r } : {}
	};
}
function qt(e) {
	let t = l(e) ? e : {}, n = l(t.toolCall) ? t.toolCall : {};
	return {
		type: "permission",
		title: m(n.title) ?? "Permission required",
		options: _(t.options)
	};
}
//#endregion
//#region src/core/protocol/connect.ts
async function Jt(e) {
	if (e.protocol === 1) return Yt(1, 1, e);
	if (e.protocol === 2) return Yt(2, 1, e);
	let t = await e.connector.open({
		protocol: 2,
		attempt: 1,
		signal: e.signal
	}), n = Zt(t);
	try {
		return await Xt(n.stream, e);
	} catch (r) {
		if (n.negotiatedVersion() !== 1) throw r;
		return await en(t), Yt(1, 2, e);
	}
}
async function Yt(e, t, r) {
	let i = await r.connector.open({
		protocol: e,
		attempt: t,
		signal: r.signal
	});
	if (r.signal.aborted) throw await en(i), new n("CONNECTION_CLOSED", "Connection was cancelled", {
		protocol: e,
		retryable: !0
	});
	return e === 1 ? Ht({
		stream: i,
		sink: r.sink,
		clientInfo: r.clientInfo,
		...r.host ? { host: r.host } : {}
	}) : Xt(i, r);
}
async function Xt(e, t) {
	let { connectV2: n } = await import("./chunks/v2.js");
	return n({
		stream: e,
		sink: t.sink,
		clientInfo: t.clientInfo,
		...t.host ? { host: t.host } : {}
	});
}
function Zt(e) {
	let t, n, r = e.writable, i = e.readable, a = new WritableStream({
		async write(e) {
			let n = Qt(e);
			n && (t = n.id);
			let i = r.getWriter();
			try {
				await i.write(e);
			} finally {
				i.releaseLock();
			}
		},
		async close() {
			let e = r.getWriter();
			try {
				await e.close();
			} finally {
				e.releaseLock();
			}
		},
		async abort(e) {
			let t = r.getWriter();
			try {
				await t.abort(e);
			} finally {
				t.releaseLock();
			}
		}
	});
	return {
		stream: {
			readable: i.pipeThrough(new TransformStream({ transform(e, r) {
				let i = Array.isArray(e) ? e : [e];
				for (let e of i) !$t(e) || e.id !== t || !$t(e.result) || typeof e.result.protocolVersion == "number" && (n = e.result.protocolVersion);
				r.enqueue(e);
			} })),
			writable: a
		},
		negotiatedVersion: () => n
	};
}
function Qt(e) {
	let t = Array.isArray(e) ? e : [e];
	for (let e of t) if ($t(e) && e.method === "initialize" && Object.hasOwn(e, "id")) return { id: e.id };
}
function $t(e) {
	return typeof e == "object" && !!e && !Array.isArray(e);
}
async function en(e) {
	try {
		let t = e.writable.getWriter();
		try {
			await t.close();
		} finally {
			t.releaseLock();
		}
	} catch {}
}
//#endregion
//#region src/core/wire-budget.ts
var tn = 2097152;
function nn(e, t = tn) {
	let n;
	try {
		n = JSON.stringify(e);
	} catch {
		return !1;
	}
	return n !== void 0 && rn(n, t);
}
function rn(e, t) {
	let n = 0;
	for (let r = 0; r < e.length; r += 1) {
		let i = e.charCodeAt(r);
		if (i <= 127 ? n += 1 : i <= 2047 ? n += 2 : i >= 55296 && i <= 56319 && r + 1 < e.length && e.charCodeAt(r + 1) >= 56320 && e.charCodeAt(r + 1) <= 57343 ? (n += 4, r += 1) : n += 3, n > t) return !1;
	}
	return !0;
}
//#endregion
//#region src/core/chat-controller.ts
var an = {
	listSessions: !1,
	loadSession: !1,
	resumeSession: !1,
	closeSession: !1,
	deleteSession: !1
}, on = 16384, sn = 16384;
function cn(e) {
	return new ln(e);
}
var ln = class {
	ready;
	#e;
	#t = /* @__PURE__ */ new Set();
	#n;
	#r;
	#i;
	#a = /* @__PURE__ */ new Map();
	#o = /* @__PURE__ */ new Map();
	#s;
	#c = /* @__PURE__ */ new Map();
	#l = /* @__PURE__ */ new Map();
	#u = [];
	#d;
	#f;
	#p = 0;
	#m = 0;
	#h = 0;
	#g = 0;
	#_ = !1;
	#v;
	#y = 0;
	#b = "connecting";
	#x;
	#S = [];
	#C;
	#w;
	#T = /* @__PURE__ */ new Map();
	#E;
	constructor(e) {
		this.#e = e, this.#C = this.#te(), this.#i = dn(e.context), this.#f = {
			phase: "connecting",
			loadedSessions: [],
			historyGap: !1,
			activities: [],
			configOptions: [],
			commands: [],
			contextSelection: this.#ae(),
			interactions: [],
			authMethods: [],
			capabilities: an,
			sessionTrail: []
		}, un(e.context) && (this.#n = e.context.subscribe(() => {
			this.#_ || this.#ie();
		})), this.ready = this.#D(!0), this.ready.catch(() => void 0);
	}
	getSnapshot() {
		return this.#f;
	}
	subscribe(e) {
		return this.#t.add(e), () => this.#t.delete(e);
	}
	appendNotice(e) {
		if (this.#_) return !1;
		if (!l(e) || typeof e.text != "string" || e.text.length === 0 || !rn(e.text, sn) || e.level !== "info" && e.level !== "error" || e.sessionId !== void 0 && (typeof e.sessionId != "string" || e.sessionId.trim().length === 0)) throw new n("INVALID_CONFIGURATION", `Notice text must contain 1 to ${sn} UTF-8 bytes, use an info or error level, and target a non-empty session ID when provided`, { phase: "notice" });
		let t = e.sessionId ?? this.#f.sessionId;
		if (!t) return !1;
		let r = this.#a.get(t);
		return r ? (r.timeline.addNotice({
			type: "notice",
			id: `host-notice-${++this.#p}`,
			text: e.text,
			level: e.level
		}), this.#$(r), !0) : !1;
	}
	send(e) {
		this.#V();
		let t = this.#Y();
		if (this.#T.has(t.sessionId)) throw new n("SESSION_BUSY", `Wait for the current operation on session '${t.sessionId}'`, {
			protocol: this.#d?.version,
			phase: "prompt"
		});
		if (t.activeTurn) throw new n("SESSION_BUSY", "Wait for the current turn to finish", {
			protocol: this.#d?.version,
			phase: "prompt"
		});
		if (t.phase !== "idle" || !this.#K().promptReady(t.sessionId)) throw new n("SESSION_BUSY", `Session '${t.sessionId}' is not ready for another prompt`, {
			protocol: this.#d?.version,
			phase: "prompt"
		});
		let r = pn(e);
		if (r.some((e) => e._meta !== null && e._meta !== void 0 && Object.hasOwn(e._meta, "pretty-aui/context"))) throw new n("INVALID_CONFIGURATION", "Prompt input cannot use the reserved pretty-aui/context metadata key", { phase: "prompt" });
		if (!r.length || r.every((e) => e.type === "text" && typeof e.text == "string" && !e.text.trim())) throw new n("INVALID_CONFIGURATION", "A prompt cannot be empty", { phase: "prompt" });
		g(r, this.#K().initialized.promptCapabilities, this.#K().version);
		let i = `turn-${++this.#p}`, a = new AbortController(), o = {
			id: i,
			sessionId: t.sessionId,
			abort: a,
			contextSelection: this.#i,
			cancelled: !1,
			submitted: !1
		};
		t.activeTurn = o, t.timeline.beginTurn(), t.timeline.addUserMessage(r, !0, Date.now()), t.phase = "running", t.stopReason = void 0, t.error = void 0, this.#$(t, !0), this.#ce({
			type: "turn_started",
			sessionId: t.sessionId,
			turnId: i
		});
		let s = this.#k(o, r);
		return s.catch(() => void 0), {
			id: i,
			done: s
		};
	}
	async addContext() {
		let e = this.#ne("add");
		if (!e.add) throw new n("METHOD_NOT_AVAILABLE", "The context provider does not support adding context", { phase: "context/add" });
		await this.#re("context/add", () => e.add());
	}
	async removeContext(e) {
		let t = this.#ne("remove");
		if (!t.remove) throw new n("METHOD_NOT_AVAILABLE", "The context provider does not support removing context", { phase: "context/remove" });
		if (!this.#i.some((t) => t.id === e)) throw new n("INVALID_CONFIGURATION", `Unknown context selection '${e}'`, { phase: "context/remove" });
		await this.#re("context/remove", () => t.remove(e));
	}
	async cancel(e) {
		let t = this.#Y(e), n = t.activeTurn;
		if (!n || n.cancelled || (n.cancelled = !0, n.abort.abort(bn), this.#z(t.sessionId), t.phase = "cancelling", this.#$(t, !0), !n.submitted)) return;
		let r = this.#d;
		if (r) try {
			await r.cancel(t.sessionId);
		} catch (e) {
			throw t.activeTurn === n && (n.cancelled = !1, this.#q(e, t.sessionId)), e;
		}
	}
	async reconnect() {
		this.#U(), await this.#ue("connection/reconnect", () => this.#D(!1));
	}
	async newSession() {
		this.#W();
		try {
			await this.#ue("session/new", async () => {
				let e = this.#K(), t = await this.#M(e), n = this.#X(t);
				this.#Z(n);
			});
		} catch (e) {
			throw this.#G(e, "session/new");
		}
	}
	async listSessions(e) {
		let t = this.#E;
		if (t) {
			if (t.cursor === e) return t.operation;
			throw new n("SESSION_BUSY", "Wait for the current session-list request to finish", {
				protocol: this.#d?.version,
				phase: "session/list"
			});
		}
		let r = this.#K(), i = Symbol("session/list"), a = Promise.resolve().then(async () => {
			try {
				let t = await r.listSessions(this.#e.session.cwd, e);
				this.#fe(r);
				let n = e && this.#f.sessions ? {
					sessions: yn([...this.#f.sessions.sessions, ...t.sessions]).slice(0, 1e3),
					...t.nextCursor ? { nextCursor: t.nextCursor } : {}
				} : t;
				return this.#f = fn({
					...this.#f,
					sessions: n
				}), this.#oe(), n;
			} finally {
				this.#E?.token === i && (this.#E = void 0);
			}
		});
		return this.#E = {
			cursor: e,
			operation: a,
			token: i
		}, a;
	}
	async openSession(e) {
		let t = ++this.#g, n = this.#a.get(e);
		if (n) {
			t === this.#g && this.#Z(n);
			return;
		}
		this.#W(), await this.#de(e, "session/open", async () => this.#j(this.#K(), e, [], t));
	}
	async openChildSession(e) {
		let t = this.#Y();
		if (this.#H(t, "session/open-child"), e === t.sessionId) return;
		let n = [...this.#f.sessionTrail, {
			sessionId: t.sessionId,
			...t.sessionTitle ? { title: t.sessionTitle } : {}
		}], r = ++this.#g, i = this.#a.get(e);
		if (i) {
			this.#Z(i, n);
			return;
		}
		this.#W(), await this.#de(e, "session/open-child", async () => this.#j(this.#K(), e, n, r));
	}
	async openAncestorSession(e) {
		this.#H(this.#Y(), "session/open-ancestor");
		let t = this.#f.sessionTrail.findIndex((t) => t.sessionId === e);
		if (t < 0) throw new n("INVALID_CONFIGURATION", `Session '${e}' is not an ancestor of the active session`, { phase: "session/open-ancestor" });
		let r = this.#f.sessionTrail.slice(0, t), i = ++this.#g, a = this.#a.get(e);
		if (a) {
			this.#Z(a, r);
			return;
		}
		this.#W(), await this.#de(e, "session/open-ancestor", async () => this.#j(this.#K(), e, r, i));
	}
	async closeSession(e) {
		let t = this.#Y(e);
		this.#H(t, "session/close"), await this.#de(t.sessionId, "session/close", async () => {
			let e = this.#K();
			if (await e.closeSession(t.sessionId), this.#fe(e), this.#z(t.sessionId), this.#a.delete(t.sessionId), this.#f.sessionId === t.sessionId) {
				let e = [...this.#a.values()].sort((e, t) => t.lastSelected - e.lastSelected)[0];
				e ? this.#Z(e) : this.#Q();
			} else this.#oe();
		});
	}
	async deleteSession(e) {
		if (e === this.#f.sessionId) throw new n("INVALID_CONFIGURATION", "The active session cannot be deleted", { phase: "session/delete" });
		let t = this.#a.get(e);
		t && this.#H(t, "session/delete"), await this.#de(e, "session/delete", async () => {
			let n = this.#K();
			await n.deleteSession(e), this.#fe(n), t && (this.#z(e), this.#a.delete(e)), this.#f.sessions && (this.#f = fn({
				...this.#f,
				sessions: {
					...this.#f.sessions,
					sessions: this.#f.sessions.sessions.filter((t) => t.sessionId !== e)
				}
			})), this.#oe();
		});
	}
	async setConfigOption(e, t) {
		let n = this.#Y();
		this.#H(n, "session/set-config"), await this.#de(n.sessionId, "session/set-config", async () => {
			let r = this.#K(), i = await r.setConfigOption(n.sessionId, e, t);
			this.#fe(r), n.configOptions = i.length ? i : n.configOptions.map((n) => n.id === e ? {
				...n,
				currentValue: t
			} : n), this.#ee(n), this.#$(n);
		});
	}
	async authenticate(e) {
		if (this.#e.allowAuthentication === !1) throw new n("AUTHENTICATION_DISABLED", "Agent authentication is disabled by the host", { phase: "auth/login" });
		let t = this.#f.authMethods.find((t) => t.id === e);
		if (!t) throw new n("INVALID_CONFIGURATION", `Unknown authentication method '${e}'`);
		await this.#ue("auth/login", async () => {
			let e = this.#K();
			this.#b = "connecting", this.#x = void 0, this.#oe();
			try {
				await e.authenticate(t), this.#fe(e);
				let n = await this.#M(e);
				this.#b = "ready";
				let r = this.#X(n);
				this.#Z(r);
			} catch (e) {
				throw this.#q(e), e;
			}
		});
	}
	async logout() {
		this.#U(), await this.#ue("auth/logout", async () => {
			let e = this.#K();
			await e.logout(), this.#fe(e), this.#z(), this.#a.clear(), this.#b = "auth_required", this.#Q();
		});
	}
	respondPermission(e, t) {
		let n = this.#c.get(e);
		return n ? (this.#c.delete(e), n.resolve(t), this.#R(e, n.sessionId), !0) : !1;
	}
	respondElicitation(e, t) {
		let n = this.#l.get(e);
		return n ? (this.#l.delete(e), n.resolve(t), this.#R(e, n.sessionId), !0) : !1;
	}
	async destroy() {
		if (this.#_) return;
		this.#_ = !0, this.#n?.(), this.#n = void 0, this.#r = void 0, this.#y += 1, this.#s?.abort();
		let e = new n("TURN_INTERRUPTED", "Chat was destroyed before the turn completed", {
			phase: "destroy",
			retryable: !1
		});
		for (let t of this.#a.values()) t.activeTurn?.abort.abort(e);
		this.#z();
		let t = this.#d;
		this.#d = void 0, this.#o.clear(), this.#b = "closed", this.#oe(), await t?.close().catch(() => void 0), this.#t.clear();
	}
	onUpdate(e, t) {
		if (this.#_) return;
		let n = this.#o.get(e), r = this.#a.get(e);
		if (!n && !r) {
			this.#ce({
				type: "diagnostic",
				sessionId: e,
				code: "UNKNOWN_SESSION_UPDATE",
				message: `Ignored an update for unloaded session '${e}'`
			});
			return;
		}
		let i = (n?.timeline ?? r.timeline).reduce(t, this.#d?.version ?? 1);
		if (n) {
			this.#F(n, i);
			return;
		}
		let a = this.#N(r, i);
		this.#$(r, a);
	}
	onPermission(e, t, n) {
		let r = this.#a.get(e);
		if (this.#_ || !r?.activeTurn || !this.#P()) return Promise.resolve({ outcome: "cancelled" });
		let i = `permission-${++this.#p}`, a = {
			...t,
			id: i
		};
		return new Promise((t) => {
			this.#c.set(i, {
				sessionId: e,
				interaction: a,
				resolve: t
			}), this.#L(a, e);
		});
	}
	onElicitation(e, t, n) {
		if (this.#_ || e !== void 0 && !this.#a.has(e) || t.elicitationId !== void 0 && this.#B(t.elicitationId) !== void 0 || !this.#P()) return Promise.resolve({ action: "cancel" });
		let r = `elicitation-${++this.#p}`, i = {
			...t,
			id: r
		};
		return new Promise((t) => {
			this.#l.set(r, {
				...e === void 0 ? {} : { sessionId: e },
				interaction: i,
				resolve: t
			}), this.#L(i, e);
		});
	}
	onElicitationComplete(e) {
		if (this.#_) return;
		let t = this.#B(e);
		if (!t) return;
		let n = this.#l.get(t);
		n && (this.#l.delete(t), n.resolve({ action: "accept" }), this.#R(t, n.sessionId));
	}
	onProtocol(e, t) {
		let n = this.#d?.version;
		n && this.#ce({
			type: "protocol",
			protocolVersion: n,
			method: e,
			raw: t
		});
	}
	onDisconnect() {
		this.#_ || (this.#z(), this.#q(new n("CONNECTION_CLOSED", "The ACP connection closed", {
			protocol: this.#d?.version,
			phase: "connection",
			retryable: !0
		})));
	}
	async #D(e) {
		if (this.#v) return this.#v;
		let t = this.#O(e);
		return this.#v = t, t.then(() => {
			this.#v === t && (this.#v = void 0);
		}, () => {
			this.#v === t && (this.#v = void 0);
		}), t;
	}
	async #O(e) {
		if (this.#_) throw z();
		let t = ++this.#y;
		this.#s?.abort();
		let r = new AbortController();
		this.#s = r, this.#b = "connecting", this.#x = void 0, this.#oe();
		let i = this.#d, a = this.#f.sessionId, o = this.#S, s = [...this.#a.values()];
		i && (this.#d = void 0, await i.close().catch(() => void 0), this.#me(t));
		let l;
		try {
			if (l = await Jt({
				connector: this.#e.connector,
				protocol: this.#e.protocol ?? 1,
				signal: r.signal,
				sink: this,
				clientInfo: {
					name: this.#e.clientInfo?.name ?? "pretty-aui",
					version: this.#e.clientInfo?.version ?? "0.1.0",
					...this.#e.clientInfo?.title ? { title: this.#e.clientInfo.title } : {}
				},
				...this.#e.host ? { host: this.#e.host } : {}
			}), !this.#pe(t)) throw await l.close().catch(() => void 0), z();
			if (this.#d = l, this.#f = fn({
				...this.#f,
				protocolVersion: l.version,
				agentName: l.initialized.agentName,
				authMethods: this.#e.allowAuthentication === !1 ? [] : l.initialized.authMethods,
				capabilities: l.initialized.capabilities
			}), this.#oe(), this.#ce({
				type: "connected",
				protocolVersion: l.version
			}), e) {
				let e = this.#e.initialSession ?? { type: "new" };
				if (e.type === "none") {
					this.#a.clear(), this.#b = "ready", this.#Q();
					return;
				}
				if (e.type === "open") {
					this.#W(), await this.#j(l, e.sessionId, [], ++this.#g), this.#b = "ready", this.#oe();
					return;
				}
				let n = await this.#M(l);
				this.#me(t, l), this.#a.clear(), this.#b = "ready", this.#Z(this.#X(n));
				return;
			}
			if (!s.length) {
				this.#b = "ready", this.#Q();
				return;
			}
			if (!l.initialized.capabilities.resumeSession && !l.initialized.capabilities.loadSession) {
				let e = await this.#M(l);
				this.#me(t, l), this.#a.clear(), this.#b = "ready", this.#Z(this.#X(e));
				return;
			}
			let n = [...s].sort((e, t) => e.sessionId === a ? -1 : t.sessionId === a ? 1 : t.lastSelected - e.lastSelected);
			for (let e of n) try {
				let n = l.initialized.capabilities.resumeSession ? "none" : "all", r = n === "none" ? e.timeline : new c(), i = {
					sessionId: e.sessionId,
					timeline: r,
					configOptions: e.configOptions,
					commands: e.commands,
					sessionTitle: e.sessionTitle
				};
				this.#o.set(e.sessionId, i);
				let s = await l.openSession(e.sessionId, this.#e.session, n);
				this.#me(t, l), n === "all" && this.#F(i, r.finalizeReplay());
				let u = this.#X(s, r, i, e.instanceId);
				u.lastSelected = e.lastSelected, u.usage = e.usage, e.sessionId === a && this.#Z(u, o);
			} catch (t) {
				if (e.sessionId === a) throw t;
				e.phase = "error", e.error = y(t), this.#a.set(e.sessionId, e);
			} finally {
				this.#o.delete(e.sessionId);
			}
			this.#b = "ready", this.#oe();
		} catch (e) {
			if (!this.#pe(t)) throw l && this.#d === l && (this.#d = void 0), await l?.close().catch(() => void 0), z();
			if (e instanceof n && e.code === "AUTHENTICATION_REQUIRED" && l?.initialized.authMethods.length) {
				if (this.#e.allowAuthentication === !1) {
					let t = new n("AUTHENTICATION_DISABLED", "The agent requires authentication disabled by the host", {
						cause: e,
						protocol: l?.version,
						phase: "session/new"
					});
					throw this.#q(t), t;
				}
				throw this.#b = "auth_required", this.#x = void 0, this.#oe(), new n("AUTHENTICATION_REQUIRED", "Authentication is required before a session can be created", {
					cause: e,
					protocol: l?.version,
					phase: "session/new"
				});
			}
			throw this.#q(e), e;
		}
	}
	async #k(e, r) {
		try {
			let i = this.#K(), o = this.#Y(e.sessionId), s = await this.#A(o.sessionId, r, e.contextSelection, e.abort.signal);
			xn(e.abort.signal);
			let c = s.map((e) => ({
				...e,
				content: e.content.map((t) => mn(t, e))
			})), l = c.length ? t(r, a()) : r, u = [...c.flatMap((e) => e.content), ...l];
			if (g(u, i.initialized.promptCapabilities, i.version), !nn({
				jsonrpc: "2.0",
				id: 2 ** 53 - 1,
				method: "session/prompt",
				params: {
					sessionId: o.sessionId,
					prompt: u
				}
			})) throw new n("INVALID_CONFIGURATION", "The prepared ACP prompt exceeds the 2 MiB wire-message limit", {
				protocol: i.version,
				phase: "prompt"
			});
			xn(e.abort.signal), e.submitted = !0;
			let d = await i.prompt(o.sessionId, u, () => {
				this.#_ || (o.timeline.markUserAccepted(c), this.#$(o));
			});
			return this.#le(e, e.cancelled ? "cancelled" : d);
		} catch (t) {
			if (e.cancelled || t === bn) return this.#le(e, "cancelled");
			let n = this.#a.get(e.sessionId);
			throw n?.activeTurn === e && (n.activeTurn = void 0, n.timeline.finishTurn()), this.#q(t, e.sessionId), t;
		}
	}
	async #A(e, t, r, i) {
		try {
			let n = this.#e.context;
			if (!n) return [];
			let a = un(n) ? await Sn(n.resolve({
				sessionId: e,
				input: t,
				selection: r,
				...this.#f.protocolVersion ? { protocolVersion: this.#f.protocolVersion } : {},
				capabilities: this.#K().initialized.promptCapabilities,
				signal: i
			}), i) : n;
			if (un(n) && (a.length !== r.length || a.some((e, t) => e.id !== r[t]?.id))) throw Error("Resolved context IDs must match the frozen selection order");
			let o = /* @__PURE__ */ new Set();
			if (a.length > 64) throw Error("Context is limited to 64 items per turn");
			for (let e of a) {
				if (!l(e) || typeof e.id != "string" || !e.id.trim() || e.id.length > 16384) throw Error("Context item IDs must be non-empty bounded strings");
				if (o.has(e.id)) throw Error(`Context item IDs must be unique: '${e.id}'`);
				if (typeof e.label != "string" || !e.label.trim() || e.label.length > 16384) throw Error("Context item labels must be non-empty bounded strings");
				if (!Array.isArray(e.content) || !e.content.length) throw Error("Context items must contain at least one content block");
				o.add(e.id);
			}
			let s = a.map((e) => ({
				id: e.id,
				label: e.label,
				content: e.content.map(hn)
			})), c = this.#K();
			return g(s.flatMap((e) => e.content), c.initialized.promptCapabilities, c.version), s;
		} catch (e) {
			throw i.aborted ? i.reason ?? e : new n("CONTEXT_FAILED", "Context could not be prepared; the prompt was not sent", {
				cause: e,
				protocol: this.#d?.version,
				phase: "context",
				retryable: !0
			});
		}
	}
	async #j(e, t, n, r) {
		let i = {
			sessionId: t,
			timeline: new c(),
			configOptions: [],
			commands: [],
			sessionTitle: void 0
		};
		this.#o.set(t, i);
		try {
			let a = await e.openSession(t, this.#e.session, "all");
			this.#fe(e), this.#F(i, i.timeline.finalizeReplay());
			let o = this.#X(a, i.timeline, i);
			r === this.#g ? this.#Z(o, n) : this.#oe();
		} finally {
			this.#o.get(t) === i && this.#o.delete(t);
		}
	}
	async #M(e) {
		let t = await e.newSession(this.#e.session);
		this.#fe(e);
		let n = _n(t.configOptions), r = this.#C;
		if (!n || !r || n.currentValue === r || !n.options?.some((e) => e.value === r)) return t;
		try {
			let i = await e.setConfigOption(t.sessionId, n.id, r);
			return this.#fe(e), {
				...t,
				configOptions: i.length ? i : t.configOptions.map((e) => e.id === n.id ? {
					...e,
					currentValue: r
				} : e)
			};
		} catch {
			if (this.#fe(e), this.#b === "error") throw z();
			return this.#ce({
				type: "diagnostic",
				sessionId: t.sessionId,
				code: "MODEL_PREFERENCE_APPLY_FAILED",
				message: "The preferred model could not be applied; using the Agent default"
			}), t;
		}
	}
	#N(e, t) {
		let n = !1;
		return t.state && !e.activeTurn && (e.phase !== "cancelling" || t.state !== "idle") ? this.#ce({
			type: "diagnostic",
			sessionId: e.sessionId,
			code: "STALE_SESSION_STATE",
			message: `Ignored ${t.state} state without an active turn`
		}) : (t.state === "running" && (e.phase = "running", n = !0), t.state === "requires_action" && (e.phase = "awaiting_user", n = !0), t.state === "idle" && (e.phase = "idle", t.stopReason && (e.stopReason = t.stopReason), n = !0)), t.commands && (e.commands = t.commands), t.configOptions && (e.configOptions = t.configOptions), t.sessionTitle !== void 0 && (e.sessionTitle = t.sessionTitle ?? void 0, n = !0), t.usage && (e.usage = t.usage), t.unsupported && this.#ce({
			type: "diagnostic",
			sessionId: e.sessionId,
			code: "UNSUPPORTED_UPDATE",
			message: t.unsupported
		}), this.#I(e.sessionId, t), n;
	}
	#P() {
		return this.#c.size + this.#l.size < 16 || (this.#ce({
			type: "diagnostic",
			code: "INTERACTION_LIMIT",
			message: "Cancelled an interaction beyond the 16-interaction limit"
		}), !1);
	}
	#F(e, t) {
		t.commands && (e.commands = t.commands), t.configOptions && (e.configOptions = t.configOptions), t.sessionTitle !== void 0 && (e.sessionTitle = t.sessionTitle ?? void 0), this.#I(e.sessionId, t);
	}
	#I(e, t) {
		for (let n of t.diagnostics ?? []) this.#ce({
			type: "diagnostic",
			sessionId: e,
			code: n.code,
			message: n.message
		});
	}
	#L(e, t) {
		if (t === void 0) {
			this.#u = [...this.#u, e], this.#oe();
			return;
		}
		let n = this.#a.get(t);
		n && (n.interactions = [...n.interactions, e], n.phase = "awaiting_user", this.#$(n, !0));
	}
	#R(e, t) {
		if (t === void 0) {
			this.#u = this.#u.filter((t) => t.id !== e), this.#oe();
			return;
		}
		let n = this.#a.get(t);
		n && (n.interactions = n.interactions.filter((t) => t.id !== e), n.phase = n.interactions.length ? "awaiting_user" : n.activeTurn ? "running" : "idle", this.#$(n, !0));
	}
	#z(e) {
		for (let [t, n] of this.#c) (e === void 0 || n.sessionId === e) && (this.#c.delete(t), n.resolve({ outcome: "cancelled" }));
		for (let [t, n] of this.#l) (e === void 0 || n.sessionId === e) && (this.#l.delete(t), n.resolve({ action: "cancel" }));
		if (e === void 0) {
			this.#u = [];
			for (let e of this.#a.values()) e.interactions = [], e.activeTurn || (e.phase = "idle");
			this.#oe();
			return;
		}
		let t = this.#a.get(e);
		t && (t.interactions = [], t.phase = t.activeTurn ? "running" : "idle", this.#$(t, !0));
	}
	#B(e) {
		for (let [t, n] of this.#l) if (n.interaction.type === "elicitation" && n.interaction.elicitationId === e) return t;
	}
	#V() {
		if (this.#_) throw new n("CONNECTION_CLOSED", "Chat has been destroyed");
		if (this.#b !== "ready" || !this.#d || !this.#f.sessionId) throw new n("SESSION_NOT_READY", "The chat session is not ready", { phase: "prompt" });
		if (this.#f.phase === "auth_required") throw new n("SESSION_NOT_READY", "Authenticate before sending a prompt", { phase: "prompt" });
	}
	#H(e, t) {
		if (e.activeTurn || e.interactions.length) throw new n("SESSION_BUSY", `Finish session '${e.sessionId}' before changing it`, { phase: t });
	}
	#U() {
		if (this.#_) throw z();
		if (this.#u.length || [...this.#a.values()].some((e) => e.activeTurn || e.interactions.length)) throw new n("SESSION_BUSY", "Finish all turns and interactions before replacing the connection", { phase: "connection/reconnect" });
	}
	#W() {
		let e = [...this.#o.keys()].filter((e) => !this.#a.has(e)).length;
		if (!(this.#a.size + e < 16)) throw new n("SESSION_LIMIT", "Close a loaded session before opening another one", { phase: "session" });
	}
	#G(e, t) {
		if (!(e instanceof n) || e.code !== "AUTHENTICATION_REQUIRED" || !this.#d?.initialized.authMethods.length) return e;
		if (this.#e.allowAuthentication === !1) {
			let r = new n("AUTHENTICATION_DISABLED", "The agent requires authentication disabled by the host", {
				cause: e,
				protocol: this.#d.version,
				phase: t
			});
			return this.#q(r), r;
		}
		return this.#b = "auth_required", this.#x = void 0, this.#oe(), new n("AUTHENTICATION_REQUIRED", "Authentication is required before a session can be created", {
			cause: e,
			protocol: this.#d.version,
			phase: t
		});
	}
	#K() {
		if (this.#_) throw z();
		if (!this.#d) throw new n("SESSION_NOT_READY", "The ACP connection is not ready");
		return this.#d;
	}
	#q(e, t) {
		if (this.#_) return;
		let n = y(e), r = t ? this.#a.get(t) : void 0;
		if (r) {
			r.phase = "error", r.error = n, this.#$(r, !0), this.#ce({
				type: "error",
				sessionId: r.sessionId,
				error: n
			});
			return;
		}
		this.#b = "error", this.#x = n, this.#oe(), this.#ce({
			type: "error",
			error: n
		});
	}
	#J() {
		let e = this.#f.sessionId;
		return e ? this.#a.get(e) : void 0;
	}
	#Y(e = this.#f.sessionId) {
		if (!e) throw new n("SESSION_NOT_READY", "No active session", { phase: "session" });
		let t = this.#a.get(e);
		if (!t) throw new n("SESSION_NOT_READY", `Session '${e}' is not loaded`, { phase: "session" });
		return t;
	}
	#X(e, t = new c(), n, r = `session-instance-${++this.#h}`) {
		let i = {
			sessionId: e.sessionId,
			instanceId: r,
			timeline: t,
			phase: "idle",
			activeTurn: void 0,
			configOptions: e.configOptions.length ? e.configOptions : n?.configOptions ?? [],
			commands: n?.commands ?? e.commands ?? [],
			interactions: [],
			sessionTitle: n?.sessionTitle,
			historyGap: e.historyGap ?? !1,
			usage: void 0,
			stopReason: void 0,
			error: void 0,
			lastSelected: 0
		};
		return this.#a.set(e.sessionId, i), i;
	}
	#Z(e, t = []) {
		e.lastSelected = ++this.#m, this.#ee(e), this.#S = [...t], this.#f = fn({
			...this.#f,
			sessionId: e.sessionId
		}), this.#oe(), this.#ce({
			type: "session_changed",
			sessionId: e.sessionId
		});
	}
	#Q() {
		this.#S = [], this.#f = fn({
			...this.#f,
			sessionId: void 0
		}), this.#oe(), this.#ce({ type: "session_changed" });
	}
	#$(e, t = !1) {
		this.#f.sessionId === e.sessionId ? (this.#ee(e), this.#oe()) : t && this.#oe();
	}
	#ee(e) {
		let t = _n(e.configOptions);
		if (!(!t || typeof t.currentValue != "string" || !vn(t.currentValue) || this.#C === t.currentValue)) {
			this.#C = t.currentValue;
			try {
				this.#e.modelPreference?.set(t.currentValue);
			} catch {
				this.#ce({
					type: "diagnostic",
					sessionId: e.sessionId,
					code: "MODEL_PREFERENCE_WRITE_FAILED",
					message: "The host could not persist the current model preference"
				});
			}
		}
	}
	#te() {
		let e;
		try {
			e = this.#e.modelPreference?.get();
		} catch {
			this.#ce({
				type: "diagnostic",
				code: "MODEL_PREFERENCE_READ_FAILED",
				message: "The host model preference could not be read"
			});
			return;
		}
		if (e !== void 0) {
			if (vn(e)) return e;
			this.#ce({
				type: "diagnostic",
				code: "INVALID_MODEL_PREFERENCE",
				message: "Ignored an invalid host model preference"
			});
		}
	}
	#ne(e) {
		if (this.#_) throw z();
		let t = this.#e.context;
		if (!un(t)) throw new n("METHOD_NOT_AVAILABLE", "The configured context is not mutable", { phase: `context/${e}` });
		return t;
	}
	async #re(e, t) {
		if (this.#_) throw z();
		if (this.#r) throw new n("SESSION_BUSY", "Wait for the current context change to finish", { phase: e });
		let r = Symbol(e);
		this.#r = r, this.#oe();
		try {
			if (await t(), this.#_ || this.#r !== r) throw z();
			this.#ie();
		} catch (t) {
			throw this.#_ ? z() : new n("CONTEXT_FAILED", "Context selection could not be changed", {
				cause: t,
				phase: e,
				retryable: !0
			});
		} finally {
			this.#r === r && (this.#r = void 0, this.#oe());
		}
	}
	#ie() {
		this.#i = dn(this.#e.context), this.#oe();
	}
	#ae() {
		let e = this.#e.context;
		return {
			items: this.#i,
			canAdd: !!(un(e) && e.add),
			canRemove: !!(un(e) && e.remove),
			busy: this.#r !== void 0
		};
	}
	#oe() {
		if (this.#_ && this.#b !== "closed") return;
		let e = this.#J(), t = this.#b, n = t === "ready" ? e?.phase ?? "idle" : t, r = t === "error" ? this.#x : e?.error;
		this.#f = fn({
			protocolVersion: this.#f.protocolVersion,
			agentName: this.#f.agentName,
			loadedSessions: [...this.#a.values()].map((e) => ({
				sessionId: e.sessionId,
				...e.sessionTitle ? { title: e.sessionTitle } : {},
				phase: e.phase,
				interactionCount: e.interactions.length,
				...e.error ? { error: e.error } : {}
			})),
			sessionId: e?.sessionId,
			sessionInstanceId: e?.instanceId,
			sessionTitle: e?.sessionTitle,
			sessionTrail: this.#S,
			historyGap: e?.historyGap ?? !1,
			activities: e?.timeline.activities ?? [],
			configOptions: e?.configOptions ?? [],
			commands: e?.commands ?? [],
			contextSelection: this.#ae(),
			interactions: [...e?.interactions ?? [], ...this.#u],
			authMethods: this.#f.authMethods,
			sessions: this.#f.sessions,
			capabilities: this.#f.capabilities,
			usage: e?.usage,
			stopReason: e?.stopReason,
			error: r,
			phase: n
		}), this.#se();
	}
	#se() {
		for (let e of this.#t) try {
			e();
		} catch {}
	}
	#ce(e) {
		if (!this.#_) try {
			this.#e.onEvent?.(e);
		} catch {}
	}
	#le(e, t) {
		if (this.#_) throw z();
		let n = this.#Y(e.sessionId);
		return n.activeTurn === e && (n.activeTurn = void 0), n.timeline.finishTurn(t === "cancelled" ? void 0 : Date.now()), n.phase = this.#d?.promptReady(n.sessionId) ? "idle" : "cancelling", n.stopReason = t, this.#$(n, !0), this.#ce({
			type: "turn_completed",
			sessionId: n.sessionId,
			turnId: e.id,
			stopReason: t
		}), { stopReason: t };
	}
	async #ue(e, t) {
		if (this.#_) throw z();
		if (this.#w) throw new n("SESSION_BUSY", "Wait for the current connection-level session operation to finish", {
			protocol: this.#d?.version,
			phase: e
		});
		if (this.#T.size) throw new n("SESSION_BUSY", "Wait for target-session operations to finish", {
			protocol: this.#d?.version,
			phase: e
		});
		let r = Symbol(e);
		this.#w = r;
		try {
			return await t();
		} finally {
			this.#w === r && (this.#w = void 0);
		}
	}
	async #de(e, t, r) {
		if (this.#_) throw z();
		if (this.#w) throw new n("SESSION_BUSY", "Wait for the current connection-level session operation to finish", {
			protocol: this.#d?.version,
			phase: t
		});
		if (this.#T.has(e)) throw new n("SESSION_BUSY", `Wait for the current operation on session '${e}'`, {
			protocol: this.#d?.version,
			phase: t
		});
		let i = Symbol(t);
		this.#T.set(e, i);
		try {
			return await r();
		} finally {
			this.#T.get(e) === i && this.#T.delete(e);
		}
	}
	#fe(e) {
		if (this.#_ || this.#d !== e) throw z();
	}
	#pe(e) {
		return !this.#_ && this.#y === e;
	}
	#me(e, t) {
		if (!this.#pe(e) || t !== void 0 && this.#d !== t) throw z();
	}
};
function un(e) {
	return !Array.isArray(e) && l(e) && typeof e.getSelection == "function" && typeof e.subscribe == "function" && typeof e.resolve == "function";
}
function dn(e) {
	if (!e) return Object.freeze([]);
	let t = un(e) ? e.getSelection() : e;
	if (!Array.isArray(t)) throw new n("INVALID_CONFIGURATION", "Context selection must be an array", { phase: "context/selection" });
	if (t.length > 64) throw new n("INVALID_CONFIGURATION", "Context is limited to 64 selected items", { phase: "context/selection" });
	let r = /* @__PURE__ */ new Set(), i = t.map((e) => {
		if (!l(e) || typeof e.id != "string" || !e.id.trim() || e.id.length > 16384) throw new n("INVALID_CONFIGURATION", "Context selection IDs must be non-empty bounded strings", { phase: "context/selection" });
		if (r.has(e.id)) throw new n("INVALID_CONFIGURATION", `Context selection IDs must be unique: '${e.id}'`, { phase: "context/selection" });
		if (typeof e.label != "string" || !e.label.trim() || e.label.length > 16384) throw new n("INVALID_CONFIGURATION", "Context selection labels must be non-empty bounded strings", { phase: "context/selection" });
		return r.add(e.id), Object.freeze({
			id: e.id,
			label: e.label
		});
	});
	return Object.freeze(i);
}
function fn(e) {
	let t = { ...e };
	for (let [e, n] of Object.entries(t)) n === void 0 && delete t[e];
	return t;
}
function pn(e) {
	return typeof e == "string" ? [{
		type: "text",
		text: e
	}] : Array.isArray(e) ? [...e] : [e];
}
function mn(e, t) {
	return {
		...e,
		_meta: {
			...e._meta ?? {},
			"pretty-aui/context": {
				version: 1,
				id: t.id,
				label: t.label
			}
		}
	};
}
function hn(e) {
	if (!l(e) || typeof e.type != "string" || !e.type) throw Error("Context content blocks require a type");
	if (l(e._meta) && Object.hasOwn(e._meta, "pretty-aui/context")) throw Error("Context blocks cannot use reserved pretty-aui metadata");
	let t = gn(e);
	switch (e.type) {
		case "text":
			if (typeof e.text != "string") throw Error("Context text blocks require text");
			return {
				...t,
				type: "text",
				text: e.text
			};
		case "image":
		case "audio":
			if (typeof e.data != "string" || typeof e.mimeType != "string") throw Error(`Context ${e.type} blocks require data and mimeType`);
			return {
				...t,
				type: e.type,
				data: e.data,
				mimeType: e.mimeType
			};
		case "resource_link":
			if (typeof e.uri != "string" || typeof e.name != "string") throw Error("Context resource links require uri and name");
			return {
				...t,
				type: "resource_link",
				uri: e.uri,
				name: e.name,
				...typeof e.title == "string" || e.title === null ? { title: e.title } : {},
				...typeof e.description == "string" || e.description === null ? { description: e.description } : {},
				...typeof e.mimeType == "string" || e.mimeType === null ? { mimeType: e.mimeType } : {},
				...typeof e.size == "number" && Number.isFinite(e.size) ? { size: e.size } : {},
				...Array.isArray(e.icons) ? { icons: e.icons.slice(0, 256).flatMap((e) => {
					let t = ee(e);
					return t ? [t] : [];
				}) } : {}
			};
		case "resource": {
			if (!l(e.resource) || typeof e.resource.uri != "string") throw Error("Context resources require a uri");
			let n = e.resource, r = n.uri, i = ee(n._meta);
			return {
				...t,
				type: "resource",
				resource: {
					uri: r,
					...typeof n.mimeType == "string" || n.mimeType === null ? { mimeType: n.mimeType } : {},
					...typeof n.text == "string" ? { text: n.text } : {},
					...typeof n.blob == "string" ? { blob: n.blob } : {},
					...i ? { _meta: i } : {}
				}
			};
		}
		default: return {
			...ee(e) ?? {},
			...t,
			type: e.type
		};
	}
}
function gn(e) {
	let t = ee(e._meta), n = l(e.annotations) ? {
		...Array.isArray(e.annotations.audience) ? { audience: e.annotations.audience.filter((e) => e === "user" || e === "assistant") } : {},
		...typeof e.annotations.priority == "number" && Number.isFinite(e.annotations.priority) ? { priority: e.annotations.priority } : {},
		...typeof e.annotations.lastModified == "string" ? { lastModified: e.annotations.lastModified.slice(0, 16384) } : {}
	} : void 0;
	return {
		...n ? { annotations: n } : {},
		...t ? { _meta: t } : {}
	};
}
function _n(e) {
	return e.find((e) => e.category === "model" && e.type === "select") ?? e.find((e) => e.id === "model" && e.type === "select");
}
function vn(e) {
	return typeof e == "string" && e.length > 0 && rn(e, on);
}
function yn(e) {
	let t = /* @__PURE__ */ new Set();
	return e.filter((e) => !t.has(e.sessionId) && (t.add(e.sessionId), !0));
}
var bn = Symbol("turn-cancelled");
function xn(e) {
	if (e.aborted) throw e.reason ?? bn;
}
function Sn(e, t) {
	return t.aborted ? Promise.reject(t.reason ?? bn) : new Promise((n, r) => {
		let i = () => {
			r(t.reason ?? bn);
		};
		t.addEventListener("abort", i, { once: !0 }), Promise.resolve(e).then((e) => {
			t.removeEventListener("abort", i), n(e);
		}, (e) => {
			t.removeEventListener("abort", i), r(e);
		});
	});
}
function z() {
	return new n("CONNECTION_CLOSED", "Chat ownership ended before the operation completed", {
		phase: "connection",
		retryable: !1
	});
}
//#endregion
//#region node_modules/.pnpm/dompurify@3.4.14/node_modules/dompurify/dist/purify.es.mjs
function Cn(e, t) {
	(t == null || t > e.length) && (t = e.length);
	for (var n = 0, r = Array(t); n < t; n++) r[n] = e[n];
	return r;
}
function wn(e) {
	if (Array.isArray(e)) return e;
}
function Tn(e, t) {
	var n = e == null ? null : typeof Symbol < "u" && e[Symbol.iterator] || e["@@iterator"];
	if (n != null) {
		var r, i, a, o, s = [], c = !0, l = !1;
		try {
			if (a = (n = n.call(e)).next, t !== 0) for (; !(c = (r = a.call(n)).done) && (s.push(r.value), s.length !== t); c = !0);
		} catch (e) {
			l = !0, i = e;
		} finally {
			try {
				if (!c && n.return != null && (o = n.return(), Object(o) !== o)) return;
			} finally {
				if (l) throw i;
			}
		}
		return s;
	}
}
function En() {
	throw TypeError("Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.");
}
function Dn(e, t) {
	return wn(e) || Tn(e, t) || On(e, t) || En();
}
function On(e, t) {
	if (e) {
		if (typeof e == "string") return Cn(e, t);
		var n = {}.toString.call(e).slice(8, -1);
		return n === "Object" && e.constructor && (n = e.constructor.name), n === "Map" || n === "Set" ? Array.from(e) : n === "Arguments" || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n) ? Cn(e, t) : void 0;
	}
}
var kn = Object.entries, An = Object.setPrototypeOf, jn = Object.isFrozen, Mn = Object.getPrototypeOf, Nn = Object.getOwnPropertyDescriptor, B = Object.freeze, V = Object.seal, Pn = Object.create, Fn = typeof Reflect < "u" && Reflect, In = Fn.apply, Ln = Fn.construct;
B ||= function(e) {
	return e;
}, V ||= function(e) {
	return e;
}, In ||= function(e, t) {
	var n = [...arguments].slice(2);
	return e.apply(t, n);
}, Ln ||= function(e) {
	return new e(...[...arguments].slice(1));
};
var Rn = W(Array.prototype.forEach), zn = W(Array.prototype.lastIndexOf), Bn = W(Array.prototype.pop), Vn = W(Array.prototype.push), Hn = W(Array.prototype.splice), Un = Array.isArray, Wn = W(String.prototype.toLowerCase), Gn = W(String.prototype.toString), Kn = W(String.prototype.match), qn = W(String.prototype.replace), Jn = W(String.prototype.indexOf), Yn = W(String.prototype.trim), Xn = W(Number.prototype.toString), Zn = W(Boolean.prototype.toString), Qn = typeof BigInt > "u" ? null : W(BigInt.prototype.toString), $n = typeof Symbol > "u" ? null : W(Symbol.prototype.toString), H = W(Object.prototype.hasOwnProperty), er = W(Object.prototype.toString), U = W(RegExp.prototype.test), tr = nr(TypeError);
function W(e) {
	return function(t) {
		t instanceof RegExp && (t.lastIndex = 0);
		var n = [...arguments].slice(1);
		return In(e, t, n);
	};
}
function nr(e) {
	return function() {
		return Ln(e, [...arguments]);
	};
}
function G(e, t) {
	let n = arguments.length > 2 && arguments[2] !== void 0 ? arguments[2] : Wn;
	if (An && An(e, null), !Un(t)) return e;
	let r = t.length;
	for (; r--;) {
		let i = t[r];
		if (typeof i == "string") {
			let e = n(i);
			e !== i && (jn(t) || (t[r] = e), i = e);
		}
		e[i] = !0;
	}
	return e;
}
function rr(e) {
	for (let t = 0; t < e.length; t++) H(e, t) || (e[t] = null);
	return e;
}
function K(e) {
	let t = Pn(null);
	for (let r of kn(e)) {
		var n = Dn(r, 2);
		let i = n[0], a = n[1];
		H(e, i) && (t[i] = Un(a) ? rr(a) : a && typeof a == "object" && a.constructor === Object ? K(a) : a);
	}
	return t;
}
function ir(e) {
	switch (typeof e) {
		case "string": return e;
		case "number": return Xn(e);
		case "boolean": return Zn(e);
		case "bigint": return Qn ? Qn(e) : "0";
		case "symbol": return $n ? $n(e) : "Symbol()";
		case "undefined": return er(e);
		case "function":
		case "object": {
			if (e === null) return er(e);
			let t = e, n = ar(t, "toString");
			if (typeof n == "function") {
				let e = n(t);
				return typeof e == "string" ? e : er(e);
			}
			return er(e);
		}
		default: return er(e);
	}
}
function ar(e, t) {
	for (; e !== null;) {
		let n = Nn(e, t);
		if (n) {
			if (n.get) return W(n.get);
			if (typeof n.value == "function") return W(n.value);
		}
		e = Mn(e);
	}
	function n() {
		return null;
	}
	return n;
}
function or(e) {
	try {
		return U(e, ""), !0;
	} catch {
		return !1;
	}
}
var sr = B(/* @__PURE__ */ "a.abbr.acronym.address.area.article.aside.audio.b.bdi.bdo.big.blink.blockquote.body.br.button.canvas.caption.center.cite.code.col.colgroup.content.data.datalist.dd.decorator.del.details.dfn.dialog.dir.div.dl.dt.element.em.fieldset.figcaption.figure.font.footer.form.h1.h2.h3.h4.h5.h6.head.header.hgroup.hr.html.i.img.input.ins.kbd.label.legend.li.main.map.mark.marquee.menu.menuitem.meter.nav.nobr.ol.optgroup.option.output.p.picture.pre.progress.q.rp.rt.ruby.s.samp.search.section.select.shadow.slot.small.source.spacer.span.strike.strong.style.sub.summary.sup.table.tbody.td.template.textarea.tfoot.th.thead.time.tr.track.tt.u.ul.var.video.wbr".split(".")), cr = B(/* @__PURE__ */ "svg.a.altglyph.altglyphdef.altglyphitem.animatecolor.animatemotion.animatetransform.circle.clippath.defs.desc.ellipse.enterkeyhint.exportparts.filter.font.g.glyph.glyphref.hkern.image.inputmode.line.lineargradient.marker.mask.metadata.mpath.part.path.pattern.polygon.polyline.radialgradient.rect.stop.style.switch.symbol.text.textpath.title.tref.tspan.view.vkern".split(".")), lr = B([
	"feBlend",
	"feColorMatrix",
	"feComponentTransfer",
	"feComposite",
	"feConvolveMatrix",
	"feDiffuseLighting",
	"feDisplacementMap",
	"feDistantLight",
	"feDropShadow",
	"feFlood",
	"feFuncA",
	"feFuncB",
	"feFuncG",
	"feFuncR",
	"feGaussianBlur",
	"feImage",
	"feMerge",
	"feMergeNode",
	"feMorphology",
	"feOffset",
	"fePointLight",
	"feSpecularLighting",
	"feSpotLight",
	"feTile",
	"feTurbulence"
]), ur = B([
	"animate",
	"color-profile",
	"cursor",
	"discard",
	"font-face",
	"font-face-format",
	"font-face-name",
	"font-face-src",
	"font-face-uri",
	"foreignobject",
	"hatch",
	"hatchpath",
	"mesh",
	"meshgradient",
	"meshpatch",
	"meshrow",
	"missing-glyph",
	"script",
	"set",
	"solidcolor",
	"unknown",
	"use"
]), dr = B(/* @__PURE__ */ "math.menclose.merror.mfenced.mfrac.mglyph.mi.mlabeledtr.mmultiscripts.mn.mo.mover.mpadded.mphantom.mroot.mrow.ms.mspace.msqrt.mstyle.msub.msup.msubsup.mtable.mtd.mtext.mtr.munder.munderover.mprescripts".split(".")), fr = B([
	"maction",
	"maligngroup",
	"malignmark",
	"mlongdiv",
	"mscarries",
	"mscarry",
	"msgroup",
	"mstack",
	"msline",
	"msrow",
	"semantics",
	"annotation",
	"annotation-xml",
	"mprescripts",
	"none"
]), pr = B(["#text"]), mr = B(/* @__PURE__ */ "accept.action.align.alt.autocapitalize.autocomplete.autopictureinpicture.autoplay.background.bgcolor.border.capture.cellpadding.cellspacing.checked.cite.class.clear.color.cols.colspan.command.commandfor.controls.controlslist.coords.crossorigin.datetime.decoding.default.dir.disabled.disablepictureinpicture.disableremoteplayback.download.draggable.enctype.enterkeyhint.exportparts.face.for.headers.height.hidden.high.href.hreflang.id.inert.inputmode.integrity.ismap.kind.label.lang.list.loading.loop.low.max.maxlength.media.method.min.minlength.multiple.muted.name.nonce.noshade.novalidate.nowrap.open.optimum.part.pattern.placeholder.playsinline.popover.popovertarget.popovertargetaction.poster.preload.pubdate.radiogroup.readonly.rel.required.rev.reversed.role.rows.rowspan.spellcheck.scope.selected.shape.size.sizes.slot.span.srclang.start.src.srcset.step.style.summary.tabindex.title.translate.type.usemap.valign.value.width.wrap.xmlns".split(".")), hr = B(/* @__PURE__ */ "accent-height.accumulate.additive.alignment-baseline.amplitude.ascent.attributename.attributetype.azimuth.basefrequency.baseline-shift.begin.bias.by.class.clip.clippathunits.clip-path.clip-rule.color.color-interpolation.color-interpolation-filters.color-profile.color-rendering.cx.cy.d.dx.dy.diffuseconstant.direction.display.divisor.dominant-baseline.dur.edgemode.elevation.end.exponent.fill.fill-opacity.fill-rule.filter.filterunits.flood-color.flood-opacity.font-family.font-size.font-size-adjust.font-stretch.font-style.font-variant.font-weight.fx.fy.g1.g2.glyph-name.glyphref.gradientunits.gradienttransform.height.href.id.image-rendering.in.in2.intercept.k.k1.k2.k3.k4.kerning.keypoints.keysplines.keytimes.lang.lengthadjust.letter-spacing.kernelmatrix.kernelunitlength.lighting-color.local.marker-end.marker-mid.marker-start.markerheight.markerunits.markerwidth.maskcontentunits.maskunits.max.mask.mask-type.media.method.mode.min.name.numoctaves.offset.operator.opacity.order.orient.orientation.origin.overflow.paint-order.path.pathlength.patterncontentunits.patterntransform.patternunits.pointer-events.points.preservealpha.preserveaspectratio.primitiveunits.r.rx.ry.radius.refx.refy.repeatcount.repeatdur.restart.result.rotate.scale.seed.shape-rendering.slope.specularconstant.specularexponent.spreadmethod.startoffset.stddeviation.stitchtiles.stop-color.stop-opacity.stroke-dasharray.stroke-dashoffset.stroke-linecap.stroke-linejoin.stroke-miterlimit.stroke-opacity.stroke.stroke-width.style.surfacescale.systemlanguage.tabindex.tablevalues.targetx.targety.transform.transform-origin.text-anchor.text-decoration.text-orientation.text-rendering.textlength.type.u1.u2.unicode.values.vector-effect.viewbox.visibility.version.vert-adv-y.vert-origin-x.vert-origin-y.width.word-spacing.wrap.writing-mode.xchannelselector.ychannelselector.x.x1.x2.xmlns.y.y1.y2.z.zoomandpan".split(".")), gr = B(/* @__PURE__ */ "accent.accentunder.align.bevelled.close.columnalign.columnlines.columnspacing.columnspan.denomalign.depth.dir.display.displaystyle.encoding.fence.frame.height.href.id.largeop.length.linethickness.lquote.lspace.mathbackground.mathcolor.mathsize.mathvariant.maxsize.minsize.movablelimits.notation.numalign.open.rowalign.rowlines.rowspacing.rowspan.rspace.rquote.scriptlevel.scriptminsize.scriptsizemultiplier.selection.separator.separators.stretchy.subscriptshift.supscriptshift.symmetric.voffset.width.xmlns".split(".")), _r = B([
	"xlink:href",
	"xml:id",
	"xlink:title",
	"xml:space",
	"xmlns:xlink"
]), vr = V(/{{[\w\W]*|^[\w\W]*}}/g), yr = V(/<%[\w\W]*|^[\w\W]*%>/g), br = V(/\${[\w\W]*/g), xr = V(/^data-[\-\w.\u00B7-\uFFFF]+$/), Sr = V(/^aria-[\-\w]+$/), Cr = V(/^(?:(?:(?:f|ht)tps?|mailto|tel|callto|sms|cid|xmpp|matrix):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i), wr = V(/^(?:\w+script|data):/i), Tr = V(/[\u0000-\u0020\u00A0\u1680\u180E\u2000-\u2029\u205F\u3000]/g), Er = V(/^html$/i), Dr = V(/^[a-z][.\w]*(-[.\w]+)+$/i), Or = V(/<[/\w!]/g), kr = V(/<[/\w]/g), Ar = V(/<\/no(script|embed|frames)/i), jr = V(/\/>/i), q = {
	element: 1,
	attribute: 2,
	text: 3,
	cdataSection: 4,
	entityReference: 5,
	entityNode: 6,
	processingInstruction: 7,
	comment: 8,
	document: 9,
	documentType: 10,
	documentFragment: 11,
	notation: 12
}, Mr = [
	"style",
	"script",
	"xmp",
	"iframe",
	"noembed",
	"noframes",
	"plaintext",
	"noscript"
], Nr = B(G({}, Mr)), Pr = function() {
	let e = {};
	return Rn(Mr, (t) => {
		e[t] = V(RegExp("</" + t + "(?=[\\t\\n\\f\\r />])", "i"));
	}), B(e);
}(), Fr = function() {
	return typeof window > "u" ? null : window;
}, Ir = function(e, t) {
	if (typeof e != "object" || typeof e.createPolicy != "function") return null;
	let n = null, r = "data-tt-policy-suffix";
	t && t.hasAttribute(r) && (n = t.getAttribute(r));
	let i = "dompurify" + (n ? "#" + n : "");
	try {
		return e.createPolicy(i, {
			createHTML(e) {
				return e;
			},
			createScriptURL(e) {
				return e;
			}
		});
	} catch {
		return console.warn("TrustedTypes policy " + i + " could not be created."), null;
	}
}, Lr = function() {
	return {
		afterSanitizeAttributes: [],
		afterSanitizeElements: [],
		afterSanitizeShadowDOM: [],
		beforeSanitizeAttributes: [],
		beforeSanitizeElements: [],
		beforeSanitizeShadowDOM: [],
		uponSanitizeAttribute: [],
		uponSanitizeElement: [],
		uponSanitizeShadowNode: []
	};
}, Rr = function(e, t, n, r) {
	return H(e, t) && Un(e[t]) ? G(r.base ? K(r.base) : {}, e[t], r.transform) : n;
}, zr = function(e, t, n) {
	let r = H(e, t) ? e[t] : void 0;
	return r && typeof r == "object" ? K(r) : n();
};
function Br() {
	let e = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : Fr(), t = (e) => Br(e);
	if (t.version = "3.4.14", t.removed = [], !e || !e.document || e.document.nodeType !== q.document || !e.Element) return t.isSupported = !1, t;
	let n = e.document, r = n, i = r.currentScript;
	e.DocumentFragment;
	let a = e.HTMLTemplateElement, o = e.Node, s = e.Element, c = e.NodeFilter;
	e.NamedNodeMap === void 0 && (e.NamedNodeMap || e.MozNamedAttrMap), e.HTMLFormElement;
	let l = e.DOMParser, u = e.trustedTypes, d = s.prototype, f = ar(d, "cloneNode"), p = ar(d, "remove"), m = ar(d, "nextSibling"), h = ar(d, "childNodes"), g = ar(d, "parentNode"), _ = ar(d, "shadowRoot"), v = ar(d, "attributes"), y = o && o.prototype ? ar(o.prototype, "nodeType") : null, b = o && o.prototype ? ar(o.prototype, "nodeName") : null, x = o && o.prototype ? ar(o.prototype, "ownerDocument") : null, S = function(e) {
		return y ? y(e) : e.nodeType;
	}, ee = function(e) {
		return b ? b(e) : e.nodeName;
	};
	if (typeof a == "function") {
		let e = n.createElement("template");
		e.content && e.content.ownerDocument && (n = e.content.ownerDocument);
	}
	let C, w = "", T, E = !1, te = 0, ne = function() {
		if (te > 0) throw tr("A configured TRUSTED_TYPES_POLICY callback (createHTML or createScriptURL) must not call DOMPurify.sanitize, as that causes infinite recursion. Do not pass a policy whose callbacks wrap DOMPurify as TRUSTED_TYPES_POLICY; see the \"DOMPurify and Trusted Types\" section of the README.");
	}, re = function(e) {
		ne(), te++;
		try {
			return C.createHTML(e);
		} finally {
			te--;
		}
	}, ie = function(e) {
		ne(), te++;
		try {
			return C.createScriptURL(e);
		} finally {
			te--;
		}
	}, ae = function() {
		return E ||= (T = Ir(u, i), !0), T;
	}, oe = n, se = oe.implementation, ce = oe.createNodeIterator, le = oe.createDocumentFragment, ue = oe.getElementsByTagName, de = r.importNode, D = Lr();
	t.isSupported = typeof kn == "function" && typeof g == "function" && se && se.createHTMLDocument !== void 0;
	let fe = vr, pe = yr, me = br, he = xr, ge = Sr, _e = wr, ve = Tr, ye = Dr, be = Cr, O = null, k = G({}, [
		...sr,
		...cr,
		...lr,
		...dr,
		...pr
	]), A = null, xe = G({}, [
		...mr,
		...hr,
		...gr,
		..._r
	]), j = Object.seal(Pn(null, {
		tagNameCheck: {
			writable: !0,
			configurable: !1,
			enumerable: !0,
			value: null
		},
		attributeNameCheck: {
			writable: !0,
			configurable: !1,
			enumerable: !0,
			value: null
		},
		allowCustomizedBuiltInElements: {
			writable: !0,
			configurable: !1,
			enumerable: !0,
			value: !1
		}
	})), Se = null, Ce = null, we = Object.seal(Pn(null, {
		tagCheck: {
			writable: !0,
			configurable: !1,
			enumerable: !0,
			value: null
		},
		attributeCheck: {
			writable: !0,
			configurable: !1,
			enumerable: !0,
			value: null
		}
	})), Te = !0, Ee = !0, De = !1, Oe = !0, ke = !1, Ae = !0, je = !1, Me = !1, Ne = null, Pe = null, Fe = !1, Ie = !1, Le = !1, Re = !1, ze = !0, Be = !1, Ve = "user-content-", He = !0, M = !1, Ue = {}, We = null, Ge = G({}, /* @__PURE__ */ "annotation-xml.audio.colgroup.desc.foreignobject.head.iframe.math.mi.mn.mo.ms.mtext.noembed.noframes.noscript.plaintext.script.selectedcontent.style.svg.template.thead.title.video.xmp".split(".")), Ke = null, N = G({}, [
		"audio",
		"video",
		"img",
		"source",
		"image",
		"track"
	]), qe = null, Je = G({}, [
		"alt",
		"class",
		"for",
		"id",
		"label",
		"name",
		"pattern",
		"placeholder",
		"role",
		"summary",
		"title",
		"value",
		"style",
		"xmlns"
	]), Ye = "http://www.w3.org/1998/Math/MathML", Xe = "http://www.w3.org/2000/svg", P = "http://www.w3.org/1999/xhtml", Ze = P, Qe = !1, F = null, $e = G({}, [
		Ye,
		Xe,
		P
	], Gn), I = B([
		"mi",
		"mo",
		"mn",
		"ms",
		"mtext"
	]), et = G({}, I), L = B(["annotation-xml"]), tt = G({}, L), nt = G({}, [
		"title",
		"style",
		"font",
		"a",
		"script"
	]), rt = null, it = ["application/xhtml+xml", "text/html"], R = null, at = null, ot = n.createElement("form"), st = function(e) {
		return e instanceof RegExp || e instanceof Function;
	}, ct = function() {
		let e = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : {};
		if (at && at === e) return;
		(!e || typeof e != "object") && (e = {}), e = K(e), rt = it.indexOf(e.PARSER_MEDIA_TYPE) === -1 ? "text/html" : e.PARSER_MEDIA_TYPE, R = rt === "application/xhtml+xml" ? Gn : Wn, O = Rr(e, "ALLOWED_TAGS", k, { transform: R }), A = Rr(e, "ALLOWED_ATTR", xe, { transform: R }), F = Rr(e, "ALLOWED_NAMESPACES", $e, { transform: Gn }), qe = Rr(e, "ADD_URI_SAFE_ATTR", Je, {
			transform: R,
			base: Je
		}), Ke = Rr(e, "ADD_DATA_URI_TAGS", N, {
			transform: R,
			base: N
		}), We = Rr(e, "FORBID_CONTENTS", Ge, { transform: R }), Se = Rr(e, "FORBID_TAGS", K({}), { transform: R }), Ce = Rr(e, "FORBID_ATTR", K({}), { transform: R }), Ue = H(e, "USE_PROFILES") ? e.USE_PROFILES && typeof e.USE_PROFILES == "object" ? K(e.USE_PROFILES) : e.USE_PROFILES : !1, Te = e.ALLOW_ARIA_ATTR !== !1, Ee = e.ALLOW_DATA_ATTR !== !1, De = e.ALLOW_UNKNOWN_PROTOCOLS || !1, Oe = e.ALLOW_SELF_CLOSE_IN_ATTR !== !1, ke = e.SAFE_FOR_TEMPLATES || !1, Ae = e.SAFE_FOR_XML !== !1, je = e.WHOLE_DOCUMENT || !1, Ie = e.RETURN_DOM || !1, Le = e.RETURN_DOM_FRAGMENT || !1, Re = e.RETURN_TRUSTED_TYPE || !1, Fe = e.FORCE_BODY || !1, ze = e.SANITIZE_DOM !== !1, Be = e.SANITIZE_NAMED_PROPS || !1, He = e.KEEP_CONTENT !== !1, M = e.IN_PLACE || !1, be = or(e.ALLOWED_URI_REGEXP) ? e.ALLOWED_URI_REGEXP : Cr, Ze = typeof e.NAMESPACE == "string" ? e.NAMESPACE : P, et = zr(e, "MATHML_TEXT_INTEGRATION_POINTS", () => G({}, I)), tt = zr(e, "HTML_INTEGRATION_POINTS", () => G({}, L));
		let t = zr(e, "CUSTOM_ELEMENT_HANDLING", () => Pn(null));
		if (j = Pn(null), H(t, "tagNameCheck") && st(t.tagNameCheck) && (j.tagNameCheck = t.tagNameCheck), H(t, "attributeNameCheck") && st(t.attributeNameCheck) && (j.attributeNameCheck = t.attributeNameCheck), H(t, "allowCustomizedBuiltInElements") && typeof t.allowCustomizedBuiltInElements == "boolean" && (j.allowCustomizedBuiltInElements = t.allowCustomizedBuiltInElements), V(j), ke && (Ee = !1), Le && (Ie = !0), Ue && (O = G({}, pr), A = Pn(null), Ue.html === !0 && (G(O, sr), G(A, mr)), Ue.svg === !0 && (G(O, cr), G(A, hr), G(A, _r)), Ue.svgFilters === !0 && (G(O, lr), G(A, hr), G(A, _r)), Ue.mathMl === !0 && (G(O, dr), G(A, gr), G(A, _r))), we.tagCheck = null, we.attributeCheck = null, H(e, "ADD_TAGS") && (typeof e.ADD_TAGS == "function" ? we.tagCheck = e.ADD_TAGS : Un(e.ADD_TAGS) && (O === k && (O = K(O)), G(O, e.ADD_TAGS, R))), H(e, "ADD_ATTR") && (typeof e.ADD_ATTR == "function" ? we.attributeCheck = e.ADD_ATTR : Un(e.ADD_ATTR) && (A === xe && (A = K(A)), G(A, e.ADD_ATTR, R))), H(e, "ADD_FORBID_CONTENTS") && Un(e.ADD_FORBID_CONTENTS) && (We === Ge && (We = K(We)), G(We, e.ADD_FORBID_CONTENTS, R)), He && (O["#text"] = !0), je && G(O, [
			"html",
			"head",
			"body"
		]), O.table && (G(O, ["tbody"]), delete Se.tbody), e.TRUSTED_TYPES_POLICY) {
			if (typeof e.TRUSTED_TYPES_POLICY.createHTML != "function") throw tr("TRUSTED_TYPES_POLICY configuration option must provide a \"createHTML\" hook.");
			if (typeof e.TRUSTED_TYPES_POLICY.createScriptURL != "function") throw tr("TRUSTED_TYPES_POLICY configuration option must provide a \"createScriptURL\" hook.");
			let t = C;
			C = e.TRUSTED_TYPES_POLICY;
			try {
				w = re("");
			} catch (e) {
				throw C = t, e;
			}
		} else e.TRUSTED_TYPES_POLICY === null ? (C = void 0, w = "") : (C === void 0 && (C = ae()), C && typeof w == "string" && (w = re("")));
		B && B(e), at = e;
	}, lt = G({}, [
		...cr,
		...lr,
		...ur
	]), ut = G({}, [...dr, ...fr]), dt = function(e, t, n) {
		return t.namespaceURI === P ? e === "svg" : t.namespaceURI === Ye ? e === "svg" && (n === "annotation-xml" || et[n]) : !!lt[e];
	}, ft = function(e, t, n) {
		return t.namespaceURI === P ? e === "math" : t.namespaceURI === Xe ? e === "math" && tt[n] : !!ut[e];
	}, pt = function(e, t, n) {
		return t.namespaceURI === Xe && !tt[n] || t.namespaceURI === Ye && !et[n] ? !1 : !ut[e] && (nt[e] || !lt[e]);
	}, mt = function(e) {
		let t = g(e);
		(!t || !t.tagName) && (t = {
			namespaceURI: Ze,
			tagName: "template"
		});
		let n = Wn(e.tagName), r = Wn(t.tagName);
		return F[e.namespaceURI] ? e.namespaceURI === Xe ? dt(n, t, r) : e.namespaceURI === Ye ? ft(n, t, r) : e.namespaceURI === P ? pt(n, t, r) : !!(rt === "application/xhtml+xml" && F[e.namespaceURI]) : !1;
	}, ht = function(e) {
		Vn(t.removed, { element: e });
		try {
			g(e).removeChild(e);
		} catch {
			if (p(e), !g(e)) throw tr("a node selected for removal could not be detached from its tree and cannot be safely returned; refusing to sanitize in place");
		}
	}, gt = function(e, t, n) {
		try {
			e.removeAttributeNode(t);
		} catch {
			try {
				e.removeAttribute(n);
			} catch {}
		}
	}, _t = function(e) {
		bt(e);
		let t = h(e);
		if (t) {
			let e = [];
			Rn(t, (t) => {
				Vn(e, t);
			}), Rn(e, (e) => {
				try {
					p(e);
				} catch {}
			});
		}
		let n = v(e);
		if (n) for (let t = n.length - 1; t >= 0; --t) {
			let r = n[t], i = r && r.name;
			typeof i == "string" && gt(e, r, i);
		}
	}, vt = function(e, n, r) {
		if (!r) try {
			r = n.getAttributeNode(e);
		} catch {
			r = null;
		}
		Vn(t.removed, {
			attribute: r || null,
			from: n
		});
		try {
			r ? n.removeAttributeNode(r) : n.removeAttribute(e);
		} catch {
			try {
				n.removeAttribute(e);
			} catch {}
		}
		if (e === "is") {
			if (Ie || Le) try {
				ht(n);
			} catch {}
			else try {
				n.setAttribute(e, "");
			} catch {}
		}
	}, yt = function(e) {
		let t = v(e);
		if (t) for (let n = t.length - 1; n >= 0; --n) {
			let r = t[n], i = r && r.name;
			typeof i != "string" || A[R(i)] || gt(e, r, i);
		}
	}, bt = function(e) {
		let t = [e];
		for (; t.length > 0;) {
			let e = t.pop();
			S(e) === q.element && yt(e);
			let n = h(e);
			if (n) for (let e = n.length - 1; e >= 0; --e) t.push(n[e]);
		}
	}, xt = function(e, t) {
		return Ae ? e === "patchsrc" || e === "for" && t !== "label" && t !== "output" : !1;
	}, St = function(e) {
		if (!Ae) return;
		let t = [e];
		for (; t.length > 0;) {
			let e = t.pop(), n = S(e);
			if (n === q.processingInstruction || n === q.comment && U(kr, e.data)) {
				try {
					p(e);
				} catch {}
				continue;
			}
			if (n === q.element) {
				let t = e, n = R(ee(e));
				try {
					t.hasAttribute && t.hasAttribute("patchsrc") && t.removeAttribute("patchsrc"), t.hasAttribute && t.hasAttribute("for") && xt("for", n) && t.removeAttribute("for");
				} catch {}
			}
			let r = h(e);
			if (r) for (let e = r.length - 1; e >= 0; --e) t.push(r[e]);
		}
	}, Ct = function(e) {
		let t = null, r = null;
		if (Fe) e = "<remove></remove>" + e;
		else {
			let t = Kn(e, /^[\r\n\t ]+/);
			r = t && t[0];
		}
		rt === "application/xhtml+xml" && Ze === P && (e = "<html xmlns=\"http://www.w3.org/1999/xhtml\"><head></head><body>" + e + "</body></html>");
		let i = C ? re(e) : e;
		if (Ze === P) try {
			t = new l().parseFromString(i, rt);
		} catch {}
		if (!t || !t.documentElement) {
			t = se.createDocument(Ze, "template", null);
			try {
				t.documentElement.innerHTML = Qe ? w : i;
			} catch {}
		}
		let a = t.body || t.documentElement;
		return e && r && a.insertBefore(n.createTextNode(r), a.childNodes[0] || null), Ze === P ? ue.call(t, je ? "html" : "body")[0] : je ? t.documentElement : a;
	}, wt = function(e) {
		let t = x ? x(e) : e.ownerDocument;
		return ce.call(t || e, e, c.SHOW_ELEMENT | c.SHOW_COMMENT | c.SHOW_TEXT | c.SHOW_PROCESSING_INSTRUCTION | c.SHOW_CDATA_SECTION, null);
	}, Tt = function(e) {
		return e = qn(e, fe, " "), e = qn(e, pe, " "), e = qn(e, me, " "), e;
	}, Et = function(e) {
		e.normalize();
		let t = x ? x(e) : e.ownerDocument, n = ce.call(t || e, e, c.SHOW_TEXT | c.SHOW_COMMENT | c.SHOW_CDATA_SECTION | c.SHOW_PROCESSING_INSTRUCTION, null), r = n.nextNode();
		for (; r;) r.data = Tt(r.data), r = n.nextNode();
		let i = e.querySelectorAll?.call(e, "template");
		i && Rn(i, (e) => {
			Ot(e.content) && Et(e.content);
		});
	}, Dt = function(e) {
		let t = b ? b(e) : null;
		return typeof t != "string" || R(t) !== "form" ? !1 : typeof e.nodeName != "string" || typeof e.textContent != "string" || typeof e.removeChild != "function" || e.attributes !== v(e) || typeof e.removeAttribute != "function" || typeof e.setAttribute != "function" || typeof e.namespaceURI != "string" || typeof e.insertBefore != "function" || typeof e.hasChildNodes != "function" || e.nodeType !== y(e) || e.childNodes !== h(e);
	}, Ot = function(e) {
		if (!y || typeof e != "object" || !e) return !1;
		try {
			return y(e) === q.documentFragment;
		} catch {
			return !1;
		}
	}, kt = function(e) {
		if (!y || typeof e != "object" || !e) return !1;
		try {
			return typeof y(e) == "number";
		} catch {
			return !1;
		}
	};
	function At(e, n, r) {
		e.length !== 0 && Rn(e, (e) => {
			e.call(t, n, r, at);
		});
	}
	let jt = function(e, t) {
		return !!(Ae && e.hasChildNodes() && !kt(e.firstElementChild) && U(Or, e.textContent) && U(Or, e.innerHTML) || Ae && e.namespaceURI === P && Nr[t] && (kt(e.firstElementChild) || typeof e.textContent == "string" && U(Pr[t], e.textContent)) || e.nodeType === q.processingInstruction || Ae && e.nodeType === q.comment && U(kr, e.data));
	}, Mt = function(e, t) {
		return e instanceof RegExp ? U(e, t) : e instanceof Function && !!e(t, ...[...arguments].slice(2));
	}, Nt = function(e, t, n) {
		if (!Se[t] && zt(t) && Mt(j.tagNameCheck, t)) return !1;
		if (He && !We[t]) {
			let t = g(e), r = h(e);
			if (r && t) {
				let i = r.length;
				for (let a = i - 1; a >= 0; --a) {
					let i = e === n ? f(r[a], !0) : r[a];
					t.insertBefore(i, m(e));
				}
			}
		}
		return ht(e), !0;
	}, Pt = function(e, t, n, r) {
		return e.length === 0 ? t : t === n || t === r ? K(t) : t;
	}, Ft = function(e, t) {
		return e === t || g(e) !== null ? !1 : (M && bt(e), !0);
	}, It = function(e, n) {
		if (At(D.beforeSanitizeElements, e, null), Ft(e, n)) return !0;
		if (Dt(e)) return ht(e), !0;
		let r = R(ee(e));
		if (O = Pt(D.uponSanitizeElement, O, k, Ne), At(D.uponSanitizeElement, e, {
			tagName: r,
			allowedTags: O
		}), Ft(e, n)) return !0;
		if (jt(e, r)) return ht(e), !0;
		if (Se[r] || !(we.tagCheck instanceof Function && we.tagCheck(r)) && !O[r]) {
			let t = Nt(e, r, n);
			return t === !1 && At(D.afterSanitizeElements, e, null), t;
		}
		if (S(e) === q.element && !mt(e) || (r === "noscript" || r === "noembed" || r === "noframes") && U(Ar, e.innerHTML)) return ht(e), !0;
		if (ke && e.nodeType === q.text) {
			let n = Tt(e.textContent);
			e.textContent !== n && (Vn(t.removed, { element: e.cloneNode() }), e.textContent = n);
		}
		return At(D.afterSanitizeElements, e, null), !1;
	}, Lt = function(e, t, r) {
		if (Ce[t] || xt(t, e) || ze && (t === "id" || t === "name") && (r in n || r in ot)) return !1;
		let i = A[t] || we.attributeCheck instanceof Function && we.attributeCheck(t, e);
		return Ee && U(he, t) || Te && U(ge, t) ? !0 : i ? qe[t] || U(be, qn(r, ve, "")) || (t === "src" || t === "xlink:href" || t === "href") && e !== "script" && Jn(r, "data:") === 0 && Ke[e] || De && !U(_e, qn(r, ve, "")) ? !0 : !r : zt(e) && Mt(j.tagNameCheck, e) && Mt(j.attributeNameCheck, t, e) || t === "is" && j.allowCustomizedBuiltInElements && Mt(j.tagNameCheck, r);
	}, Rt = G({}, [
		"annotation-xml",
		"color-profile",
		"font-face",
		"font-face-format",
		"font-face-name",
		"font-face-src",
		"font-face-uri",
		"missing-glyph"
	]), zt = function(e) {
		return !Rt[Wn(e)] && U(ye, e);
	}, Bt = function(e, t, n, r) {
		if (C && typeof u == "object" && typeof u.getAttributeType == "function" && !n) switch (u.getAttributeType(e, t)) {
			case "TrustedHTML": return re(r);
			case "TrustedScriptURL": return ie(r);
		}
		return r;
	}, Vt = function(e, n, r, i) {
		try {
			r ? e.setAttributeNS(r, n, i) : e.setAttribute(n, i), Dt(e) ? ht(e) : Bn(t.removed);
		} catch {
			vt(n, e);
		}
	}, Ht = function(e) {
		At(D.beforeSanitizeAttributes, e, null);
		let t = e.attributes;
		if (!t || Dt(e)) return;
		A = Pt(D.uponSanitizeAttribute, A, xe, Pe);
		let n = {
			attrName: "",
			attrValue: "",
			keepAttr: !0,
			allowedAttributes: A,
			forceKeepAttr: void 0
		}, r = t.length, i = R(e.nodeName);
		for (; r--;) {
			let a = t[r], o = a.name, s = a.namespaceURI, c = a.value, l = R(o), u = c, d = o === "value" ? u : Yn(u);
			if (n.attrName = l, n.attrValue = d, n.keepAttr = !0, n.forceKeepAttr = void 0, At(D.uponSanitizeAttribute, e, n), d = n.attrValue, Be && (l === "id" || l === "name") && Jn(d, Ve) !== 0 && (vt(o, e, a), d = Ve + d), Ae && U(/((--!?|])>)|<\/(style|script|title|xmp|textarea|noscript|iframe|noembed|noframes)/i, d)) {
				vt(o, e, a);
				continue;
			}
			if (l === "attributename" && Kn(d, "href")) {
				vt(o, e, a);
				continue;
			}
			if (!n.forceKeepAttr) {
				if (!n.keepAttr) {
					vt(o, e, a);
					continue;
				}
				if (!Oe && U(jr, d)) {
					vt(o, e, a);
					continue;
				}
				if (ke && (d = Tt(d)), !Lt(i, l, d)) {
					vt(o, e, a);
					continue;
				}
				d = Bt(i, l, s, d), d !== u && Vt(e, o, s, d);
			}
		}
		At(D.afterSanitizeAttributes, e, null);
	}, Ut = function(e) {
		let t = null, n = wt(e);
		for (At(D.beforeSanitizeShadowDOM, e, null); t = n.nextNode();) if (At(D.uponSanitizeShadowNode, t, null), It(t, e), Ht(t), Ot(t.content) && Ut(t.content), S(t) === q.element) {
			let e = _(t);
			Ot(e) && (Wt(e), Ut(e));
		}
		At(D.afterSanitizeShadowDOM, e, null);
	}, Wt = function(e) {
		let t = [{
			node: e,
			shadow: null
		}];
		for (; t.length > 0;) {
			let e = t.pop();
			if (e.shadow) {
				Ut(e.shadow);
				continue;
			}
			let n = e.node, r = S(n) === q.element, i = h(n);
			if (i) for (let e = i.length - 1; e >= 0; --e) t.push({
				node: i[e],
				shadow: null
			});
			if (r) {
				let e = b ? b(n) : null;
				if (typeof e == "string" && R(e) === "template") {
					let e = n.content;
					Ot(e) && t.push({
						node: e,
						shadow: null
					});
				}
			}
			if (r) {
				let e = _(n);
				Ot(e) && t.push({
					node: null,
					shadow: e
				}, {
					node: e,
					shadow: null
				});
			}
		}
	};
	return t.sanitize = function(e) {
		let n = arguments.length > 1 && arguments[1] !== void 0 ? arguments[1] : {}, i = null, a = null, o = null, s = null;
		if (Qe = !e, Qe && (e = "<!-->"), typeof e != "string" && !kt(e) && (e = ir(e), typeof e != "string")) throw tr("dirty is not a string, aborting");
		if (!t.isSupported) return e;
		Me ? (O = Ne, A = Pe) : ct(n), (D.uponSanitizeElement.length > 0 || D.uponSanitizeAttribute.length > 0) && (O = K(O)), D.uponSanitizeAttribute.length > 0 && (A = K(A)), t.removed = [];
		let c = M && typeof e != "string" && kt(e);
		if (c) {
			St(e);
			let t = ee(e);
			if (typeof t == "string") {
				let n = R(t);
				if (!O[n] || Se[n]) throw _t(e), tr("root node is forbidden and cannot be sanitized in-place");
			}
			if (Dt(e)) throw _t(e), tr("root node is clobbered and cannot be sanitized in-place");
			try {
				Wt(e);
			} catch (t) {
				throw _t(e), t;
			}
		} else if (kt(e)) i = Ct("<!---->"), a = i.ownerDocument.importNode(e, !0), a.nodeType === q.element && a.nodeName === "BODY" || a.nodeName === "HTML" ? i = a : i.appendChild(a), Wt(a);
		else {
			if (!Ie && !ke && !je && e.indexOf("<") === -1) return C && Re ? re(e) : e;
			if (i = Ct(e), !i) return Ie ? null : Re ? w : "";
		}
		i && Fe && ht(i.firstChild);
		let l = c ? e : i;
		try {
			let e = wt(l);
			for (; o = e.nextNode();) It(o, l), Ht(o), Ot(o.content) && Ut(o.content);
		} catch (n) {
			throw c && (_t(e), Rn(t.removed, (e) => {
				e.element && bt(e.element);
			})), n;
		}
		if (c) return Rn(t.removed, (e) => {
			e.element && bt(e.element);
		}), ke && Et(e), e;
		if (Ie) {
			if (ke && Et(i), Le) for (s = le.call(i.ownerDocument); i.firstChild;) s.appendChild(i.firstChild);
			else s = i;
			return (A.shadowroot || A.shadowrootmode) && (s = de.call(r, s, !0)), s;
		}
		let u = je ? i.outerHTML : i.innerHTML;
		return je && O["!doctype"] && i.ownerDocument && i.ownerDocument.doctype && i.ownerDocument.doctype.name && U(Er, i.ownerDocument.doctype.name) && (u = "<!DOCTYPE " + i.ownerDocument.doctype.name + ">\n" + u), ke && (u = Tt(u)), C && Re ? re(u) : u;
	}, t.setConfig = function() {
		let e = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : {};
		ct(e), Me = !0, Ne = O, Pe = A;
	}, t.clearConfig = function() {
		at = null, Me = !1, Ne = null, Pe = null, C = T, w = "";
	}, t.isValidAttribute = function(e, t, n) {
		at || ct({});
		let r = R(e), i = R(t);
		return Lt(r, i, n);
	}, t.addHook = function(e, t) {
		typeof t == "function" && H(D, e) && Vn(D[e], t);
	}, t.removeHook = function(e, t) {
		if (H(D, e)) {
			if (t !== void 0) {
				let n = zn(D[e], t);
				return n === -1 ? void 0 : Hn(D[e], n, 1)[0];
			}
			return Bn(D[e]);
		}
	}, t.removeHooks = function(e) {
		H(D, e) && (D[e] = []);
	}, t.removeAllHooks = function() {
		D = Lr();
	}, t;
}
var Vr = Br();
//#endregion
//#region node_modules/.pnpm/marked@18.0.10/node_modules/marked/lib/marked.esm.js
function Hr() {
	return {
		async: !1,
		breaks: !1,
		extensions: null,
		gfm: !0,
		hooks: null,
		pedantic: !1,
		renderer: null,
		silent: !1,
		tokenizer: null,
		walkTokens: null
	};
}
var Ur = Hr();
function Wr(e) {
	Ur = e;
}
var Gr = { exec: () => null };
function Kr(e) {
	let t = [];
	return (n) => {
		let r = Math.max(0, Math.min(3, n - 1)), i = t[r];
		return i || (i = e(r), t[r] = i), i;
	};
}
function J(e, t = "") {
	let n = typeof e == "string" ? e : e.source, r = {
		replace: (e, t) => {
			let i = typeof t == "string" ? t : t.source;
			return i = i.replace(Y.caret, "$1"), n = n.replace(e, i), r;
		},
		getRegex: () => new RegExp(n, t)
	};
	return r;
}
var qr = ((e = "") => {
	try {
		return !!RegExp("(?<=1)(?<!1)" + e);
	} catch {
		return !1;
	}
})(), Y = {
	codeRemoveIndent: /^(?: {1,4}| {0,3}\t)/gm,
	outputLinkReplace: /\\([\[\]])/g,
	indentCodeCompensation: /^(\s+)(?:```)/,
	beginningSpace: /^\s+/,
	endingHash: /#$/,
	startingSpaceChar: /^ /,
	endingSpaceChar: / $/,
	nonSpaceChar: /[^ ]/,
	newLineCharGlobal: /\n/g,
	tabCharGlobal: /\t/g,
	multipleSpaceGlobal: /\s+/g,
	blankLine: /^[ \t]*$/,
	doubleBlankLine: /\n[ \t]*\n[ \t]*$/,
	blockquoteStart: /^ {0,3}>/,
	blockquoteSetextReplace: /\n {0,3}((?:=+|-+) *)(?=\n|$)/g,
	blockquoteSetextReplace2: /^ {0,3}>[ \t]?/gm,
	listReplaceNesting: /^ {1,4}(?=( {4})*[^ ])/g,
	listIsTask: /^\[[ xX]\] +\S/,
	listReplaceTask: /^\[[ xX]\] +/,
	listTaskCheckbox: /\[[ xX]\]/,
	anyLine: /\n.*\n/,
	hrefBrackets: /^<(.*)>$/,
	tableDelimiter: /[:|]/,
	tableAlignChars: /^\||\| *$/g,
	tableRowBlankLine: /\n[ \t]*$/,
	tableAlignRight: /^ *-+: *$/,
	tableAlignCenter: /^ *:-+: *$/,
	tableAlignLeft: /^ *:-+ *$/,
	startATag: /^<a /i,
	endATag: /^<\/a>/i,
	startPreScriptTag: /^<(pre|code|kbd|script)(\s|>)/i,
	endPreScriptTag: /^<\/(pre|code|kbd|script)(\s|>)/i,
	startAngleBracket: /^</,
	endAngleBracket: />$/,
	pedanticHrefTitle: /^([^'"]*[^\s])\s+(['"])(.*)\2/,
	unicodeAlphaNumeric: /[\p{L}\p{N}]/u,
	escapeTest: /[&<>"']/,
	escapeReplace: /[&<>"']/g,
	escapeTestNoEncode: /[<>"']|&(?!(#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);)/,
	escapeReplaceNoEncode: /[<>"']|&(?!(#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);)/g,
	caret: /(^|[^\[])\^/g,
	percentDecode: /%25/g,
	findPipe: /\|/g,
	splitPipe: / \|/,
	slashPipe: /\\\|/g,
	carriageReturn: /\r\n|\r/g,
	spaceLine: /^ +$/gm,
	notSpaceStart: /^\S*/,
	endingNewline: /\n$/,
	listItemRegex: (e) => RegExp(`^( {0,3}${e})((?:[	 ][^\\n]*)?(?:\\n|$))`),
	nextBulletRegex: Kr((e) => RegExp(`^ {0,${e}}(?:[*+-]|\\d{1,9}[.)])((?:[ 	][^\\n]*)?(?:\\n|$))`)),
	hrRegex: Kr((e) => RegExp(`^ {0,${e}}((?:- *){3,}|(?:_ *){3,}|(?:\\* *){3,})(?:\\n+|$)`)),
	fencesBeginRegex: Kr((e) => RegExp(`^ {0,${e}}(?:\`\`\`|~~~)`)),
	headingBeginRegex: Kr((e) => RegExp(`^ {0,${e}}#`)),
	htmlBeginRegex: Kr((e) => RegExp(`^ {0,${e}}<(?:[a-z].*>|!--)`, "i")),
	blockquoteBeginRegex: Kr((e) => RegExp(`^ {0,${e}}>`))
}, Jr = /^(?:[ \t]*(?:\n|$))+/, Yr = /^((?: {4}| {0,3}\t)[^\n]+(?:\n(?:[ \t]*(?:\n|$))*)?)+/, Xr = /^ {0,3}(`{3,}(?=[^`\n]*(?:\n|$))|~{3,})([^\n]*)(?:\n|$)(?:|([\s\S]*?)(?:\n|$))(?: {0,3}\1[~`]* *(?=\n|$)|$)/, Zr = /^ {0,3}((?:-[\t ]*){3,}|(?:_[ \t]*){3,}|(?:\*[ \t]*){3,})(?:\n+|$)/, Qr = /^ {0,3}(#{1,6})(?=\s|$)(.*)(?:\n+|$)/, $r = / {0,3}(?:[*+-]|\d{1,9}[.)])/, ei = /^(?!bull |blockCode|fences|blockquote|heading|html|table)((?:.|\n(?!\s*?\n|bull |blockCode|fences|blockquote|heading|html|table))+?)\n {0,3}(=+|-+) *(?:\n+|$)/, ti = J(ei).replace(/bull/g, $r).replace(/blockCode/g, /(?: {4}| {0,3}\t)/).replace(/fences/g, / {0,3}(?:`{3,}|~{3,})/).replace(/blockquote/g, / {0,3}>/).replace(/heading/g, / {0,3}#{1,6}(?:\s|$)/).replace(/html/g, / {0,3}<[^\n>]+>\n/).replace(/\|table/g, "").getRegex(), ni = J(ei).replace(/bull/g, $r).replace(/blockCode/g, /(?: {4}| {0,3}\t)/).replace(/fences/g, / {0,3}(?:`{3,}|~{3,})/).replace(/blockquote/g, / {0,3}>/).replace(/heading/g, / {0,3}#{1,6}(?:\s|$)/).replace(/html/g, / {0,3}<[^\n>]+>\n/).replace(/table/g, / {0,3}\|?(?:[:\- ]*\|)+[\:\- ]*\n/).getRegex(), ri = /^([^\n]+(?:\n(?!hr|heading|lheading|blockquote|fences|list|html|table|[ \t]+\n)[^\n]+)*)/, ii = /^[^\n]+/, ai = /(?!\s*\])(?:\\[\s\S]|[^\[\]\\])+/, oi = J(/^ {0,3}\[(label)\]: *(?:\n[ \t]*)?([^<\s][^\s]*|<.*?>)(?:(?: +(?:\n[ \t]*)?| *\n[ \t]*)(title))? *(?:\n+|$)/).replace("label", ai).replace("title", /(?:"(?:\\"?|[^"\\])*"|'[^'\n]*(?:\n[^'\n]+)*\n?'|\([^()]*\))/).getRegex(), si = J(/^(bull)([ \t][^\n]*?)?(?:\n|$)/).replace(/bull/g, $r).getRegex(), ci = "address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|frameset|h[1-6]|head|header|hr|html|iframe|legend|li|link|main|menu|menuitem|meta|nav|noframes|ol|optgroup|option|p|param|search|section|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul", li = /<!--(?:-?>|[\s\S]*?(?:-->|$))/, ui = J("^ {0,3}(?:<(script|pre|style|textarea)[\\s>][\\s\\S]*?(?:</\\1>[^\\n]*\\n*|$)|comment[^\\n]*(\\n+|$)|<\\?[\\s\\S]*?(?:\\?>[^\\n]*\\n*|$)|<![A-Z][\\s\\S]*?(?:>[^\\n]*\\n*|$)|<!\\[CDATA\\[[\\s\\S]*?(?:\\]\\]>[^\\n]*\\n*|$)|</?(tag)(?: +|\\n|/?>)[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$)|<(?!script|pre|style|textarea)([a-z][\\w-]*)(?:attribute)*? */?>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$)|</(?!script|pre|style|textarea)[a-z][\\w-]*\\s*>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$))", "i").replace("comment", li).replace("tag", ci).replace("attribute", / +[a-zA-Z:_][\w.:-]*(?: *= *"[^"\n]*"| *= *'[^'\n]*'| *= *[^\s"'=<>`]+)?/).getRegex(), di = (e) => J(ri).replace("hr", Zr).replace("heading", " {0,3}#{1,6}(?:\\s|$)").replace("|lheading", "").replace("|table", "").replace("blockquote", " {0,3}>").replace("fences", " {0,3}(?:`{3,}(?=[^`\\n]*(?:\\n|$))|~~~)[^\\n]*(?:\\n|$)").replace("list", e).replace("html", "</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag", ci).getRegex(), fi = di(/ {0,3}(?:[*+-]|1[.)])[ \t]+[^ \t\n]/), pi = di(/ {0,3}(?:[*+-]|\d{1,9}[.)])(?:[ \t]|\n|$)/), mi = {
	blockquote: J(/^( {0,3}> ?(paragraph|[^\n]*)(?:\n|$))+/).replace("paragraph", pi).getRegex(),
	code: Yr,
	def: oi,
	fences: Xr,
	heading: Qr,
	hr: Zr,
	html: ui,
	lheading: ti,
	list: si,
	newline: Jr,
	paragraph: fi,
	table: Gr,
	text: ii
}, hi = J("^ *([^\\n ].*)\\n {0,3}((?:\\| *)?:?-+:? *(?:\\| *:?-+:? *)*(?:\\| *)?)(?:\\n((?:(?! *\\n|hr|heading|blockquote|code|fences|list|html).*(?:\\n|$))*)\\n*|$)").replace("hr", Zr).replace("heading", " {0,3}#{1,6}(?:\\s|$)").replace("blockquote", " {0,3}>").replace("code", "(?: {4}| {0,3}	)[^\\n]").replace("fences", " {0,3}(?:`{3,}(?=[^`\\n]*(?:\\n|$))|~~~)[^\\n]*(?:\\n|$)").replace("list", " {0,3}(?:[*+-]|1[.)])[ \\t]").replace("html", "</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag", ci).getRegex(), gi = {
	...mi,
	lheading: ni,
	table: hi,
	paragraph: J(ri).replace("hr", Zr).replace("heading", " {0,3}#{1,6}(?:\\s|$)").replace("|lheading", "").replace("table", hi).replace("blockquote", " {0,3}>").replace("fences", " {0,3}(?:`{3,}(?=[^`\\n]*(?:\\n|$))|~~~)[^\\n]*(?:\\n|$)").replace("list", " {0,3}(?:[*+-]|1[.)])[ \\t]+[^ \\t\\n]").replace("html", "</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag", ci).getRegex()
}, _i = {
	...mi,
	html: J("^ *(?:comment *(?:\\n|\\s*$)|<(tag)[\\s\\S]+?</\\1> *(?:\\n{2,}|\\s*$)|<tag(?:\"[^\"]*\"|'[^']*'|\\s[^'\"/>\\s]*)*?/?> *(?:\\n{2,}|\\s*$))").replace("comment", li).replace(/tag/g, "(?!(?:a|em|strong|small|s|cite|q|dfn|abbr|data|time|code|var|samp|kbd|sub|sup|i|b|u|mark|ruby|rt|rp|bdi|bdo|span|br|wbr|ins|del|img)\\b)\\w+(?!:|[^\\w\\s@]*@)\\b").getRegex(),
	def: /^ *\[([^\]]+)\]: *<?([^\s>]+)>?(?: +(["(][^\n]+[")]))? *(?:\n+|$)/,
	heading: /^(#{1,6})(.*)(?:\n+|$)/,
	fences: Gr,
	lheading: /^(.+?)\n {0,3}(=+|-+) *(?:\n+|$)/,
	paragraph: J(ri).replace("hr", Zr).replace("heading", " *#{1,6} *[^\n]").replace("lheading", ti).replace("|table", "").replace("blockquote", " {0,3}>").replace("|fences", "").replace("|list", "").replace("|html", "").replace("|tag", "").getRegex()
}, vi = /^\\([!"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])/, yi = /^(`+)([^`]|[^`][\s\S]*?[^`])\1(?!`)/, bi = /^( {2,}|\\)\n(?!\s*$)/, xi = /^(`+|[^`])(?:(?= {2,}\n)|[\s\S]*?(?:(?=[\\<!\[`*_]|\b_|$)|[^ ](?= {2,}\n)))/, Si = /[\p{P}\p{S}]/u, Ci = /[\s\p{P}\p{S}]/u, wi = /[^\s\p{P}\p{S}]/u, Ti = J(/^((?![*_])punctSpace)/, "u").replace(/punctSpace/g, Ci).getRegex(), Ei = /[\p{Pi}\p{Ps}"']/u, Di = /(?!~)[\p{P}\p{S}]/u, Oi = /(?!~)[\s\p{P}\p{S}]/u, ki = /(?:[^\s\p{P}\p{S}]|~)/u, Ai = J(/link|precode-code|html/, "g").replace("link", /\[(?:[^\[\]`]|(?<a>`+)[^`]+\k<a>(?!`))*?\]\((?:\\[\s\S]|[^\\\(\)]|\((?:\\[\s\S]|[^\\\(\)])*\))*\)/).replace("precode-", qr ? "(?<!`)()" : "(^^|[^`])").replace("code", /(?<b>`+)[^`]+\k<b>(?!`)/).replace("html", /<(?! )[^<>]*?>/).getRegex(), ji = /^(?:\*+(?:((?!\*)punct)|([^\s*]))?)|^_+(?:((?!_)punct)|([^\s_]))?/, Mi = J(ji, "u").replace(/punct/g, Si).getRegex(), Ni = J(ji, "u").replace(/punct/g, Di).getRegex(), Pi = J(/^(?:\*+(?:((?!\*)(?!openQuote)punct)|([^\s*]))?)|^_+(?:((?!_)(?!openQuote)punct)|([^\s_]))?/, "u").replace(/openQuote/g, Ei).replace(/punct/g, Si).getRegex(), Fi = "^[^_*]*?__[^_*]*?\\*[^_*]*?(?=__)|[^*]+(?=[^*])|(?!\\*)punct(\\*+)(?=[\\s]|$)|notPunctSpace(\\*+)(?!\\*)(?=punctSpace|$)|(?!\\*)punctSpace(\\*+)(?=notPunctSpace)|[\\s](\\*+)(?!\\*)(?=punct)|(?!\\*)punct(\\*+)(?!\\*)(?=punct)|notPunctSpace(\\*+)(?=notPunctSpace)", Ii = J(Fi, "gu").replace(/notPunctSpace/g, wi).replace(/punctSpace/g, Ci).replace(/punct/g, Si).getRegex(), Li = J(Fi, "gu").replace(/notPunctSpace/g, ki).replace(/punctSpace/g, Oi).replace(/punct/g, Di).getRegex(), Ri = J("^[^_*]*?__[^_*]*?\\*[^_*]*?(?=__)|[^*]+(?=[^*])|(?!\\*)punct(\\*+)(?=[\\s]|$)|notPunctSpace(\\*+)(?!\\*)(?=punctSpace|$)|(?!\\*)[\\s](\\*+)(?=notPunctSpace)|[\\s](\\*+)(?!\\*)(?=punct)|(?!\\*)punct(\\*+)(?!\\*)(?=punct)|(?:(?!\\*)punct|notPunctSpace)(\\*+)(?!\\*)(?=notPunctSpace)", "gu").replace(/notPunctSpace/g, wi).replace(/punctSpace/g, Ci).replace(/punct/g, Si).getRegex(), zi = J("^[^_*]*?\\*\\*[^_*]*?_[^_*]*?(?=\\*\\*)|[^_]+(?=[^_])|(?!_)punct(_+)(?=[\\s]|$)|notPunctSpace(_+)(?!_)(?=punctSpace|$)|(?!_)punctSpace(_+)(?=notPunctSpace)|[\\s](_+)(?!_)(?=punct)|(?!_)punct(_+)(?!_)(?=punct)", "gu").replace(/notPunctSpace/g, wi).replace(/punctSpace/g, Ci).replace(/punct/g, Si).getRegex(), Bi = J("^[^_*]*?\\*\\*[^_*]*?_[^_*]*?(?=\\*\\*)|[^_]+(?=[^_])|(?!_)punct(_+)(?=[\\s]|$)|notPunctSpace(_+)(?!_)(?=punctSpace|$)|(?!_)[\\s](_+)(?=notPunctSpace)|[\\s](_+)(?!_)(?=punct)|(?!_)punct(_+)(?!_)(?=punct)|(?:(?!_)punct|notPunctSpace)(_+)(?!_)(?=notPunctSpace)", "gu").replace(/notPunctSpace/g, wi).replace(/punctSpace/g, Ci).replace(/punct/g, Si).getRegex(), Vi = J(/^~~?(?:((?!~)punct)|[^\s~])/, "u").replace(/punct/g, Si).getRegex(), Hi = J("^[^~]+(?=[^~])|(?!~)punct(~~?)(?=[\\s]|$)|notPunctSpace(~~?)(?!~)(?=punctSpace|$)|(?!~)punctSpace(~~?)(?=notPunctSpace)|[\\s](~~?)(?!~)(?=punct)|(?!~)punct(~~?)(?!~)(?=punct)|notPunctSpace(~~?)(?=notPunctSpace)", "gu").replace(/notPunctSpace/g, wi).replace(/punctSpace/g, Ci).replace(/punct/g, Si).getRegex(), Ui = J(/\\(punct)/, "gu").replace(/punct/g, Si).getRegex(), Wi = J(/^<(scheme:[^\s\x00-\x1f<>]*|email)>/).replace("scheme", /[a-zA-Z][a-zA-Z0-9+.-]{1,31}/).replace("email", /[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+(@)[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+(?![-_])/).getRegex(), Gi = J(li).replace("(?:-->|$)", "-->").getRegex(), Ki = J("^comment|^</[a-zA-Z][\\w:-]*\\s*>|^<[a-zA-Z][\\w-]*(?:attribute)*?\\s*/?>|^<\\?[\\s\\S]*?\\?>|^<![a-zA-Z]+\\s[\\s\\S]*?>|^<!\\[CDATA\\[[\\s\\S]*?\\]\\]>").replace("comment", Gi).replace("attribute", /\s+[a-zA-Z:_][\w.:-]*(?:\s*=\s*"[^"]*"|\s*=\s*'[^']*'|\s*=\s*[^\s"'=<>`]+)?/).getRegex(), qi = /(?:\[(?:\\[\s\S]|[^\[\]\\])*\]|\\[\s\S]|`+(?!`)[^`]*?`+(?!`)|``+(?=\])|[^\[\]\\`])*?/, Ji = J(/^!?\[(label)\]\(\s*(href)(?:(?:[ \t]+(?:\n[ \t]*)?|\n[ \t]*)(title))?\s*\)/).replace("label", qi).replace("href", /<(?:\\.|[^\n<>\\])+>|[^ \t\n\x00-\x1f]+|(?=\))/).replace("title", /"(?:\\"?|[^"\\])*"|'(?:\\'?|[^'\\])*'|\((?:\\\)?|[^)\\])*\)/).getRegex(), Yi = J(/^!?\[(label)\]\[(ref)\]/).replace("label", qi).replace("ref", ai).getRegex(), Xi = J(/^!?\[(ref)\](?:\[\])?/).replace("ref", ai).getRegex(), Zi = J("reflink|nolink(?!\\()", "g").replace("reflink", Yi).replace("nolink", Xi).getRegex(), Qi = /[hH][tT][tT][pP][sS]?|[fF][tT][pP]/, $i = {
	_backpedal: Gr,
	anyPunctuation: Ui,
	autolink: Wi,
	blockSkip: Ai,
	br: bi,
	code: yi,
	del: Gr,
	delLDelim: Gr,
	delRDelim: Gr,
	emStrongLDelim: Mi,
	emStrongRDelimAst: Ii,
	emStrongRDelimUnd: zi,
	escape: vi,
	link: Ji,
	nolink: Xi,
	punctuation: Ti,
	reflink: Yi,
	reflinkSearch: Zi,
	tag: Ki,
	text: xi,
	url: Gr
}, ea = {
	...$i,
	emStrongLDelim: Pi,
	emStrongRDelimAst: Ri,
	emStrongRDelimUnd: Bi,
	link: J(/^!?\[(label)\]\((.*?)\)/).replace("label", qi).getRegex(),
	reflink: J(/^!?\[(label)\]\s*\[([^\]]*)\]/).replace("label", qi).getRegex()
}, ta = {
	...$i,
	emStrongRDelimAst: Li,
	emStrongLDelim: Ni,
	delLDelim: Vi,
	delRDelim: Hi,
	url: J(/^((?:protocol):\/\/|www\.)(?:[a-zA-Z0-9\-]+\.?)+[^\s<]*|^email/).replace("protocol", Qi).replace("email", /[A-Za-z0-9._+-]+(@)[a-zA-Z0-9-_]+(?:\.[a-zA-Z0-9-_]*[a-zA-Z0-9])+(?![-_])/).getRegex(),
	_backpedal: /(?:[^?!.,:;*_'"~()&]+|\([^)]*\)|&(?![a-zA-Z0-9]+;$)|[?!.,:;*_'"~)]+(?!$))+/,
	del: /^(~~?)(?=[^\s~])((?:\\[\s\S]|[^\\])*?(?:\\[\s\S]|[^\s~\\]))\1(?=[^~]|$)/,
	text: J(/^(`+|~+|[^`~])(?:(?=[`~])|(?= {2,}\n)|(?=[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@)|[\s\S]*?(?:(?=[\\<!\[`*~_]|\b_|protocol:\/\/|www\.|$)|[^ ](?= {2,}\n)|[^a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-](?=[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@)))/).replace("protocol", Qi).getRegex()
}, na = {
	...ta,
	br: J(bi).replace("{2,}", "*").getRegex(),
	text: J(ta.text).replace("\\b_", "\\b_| {2,}\\n").replace(/\{2,\}/g, "*").getRegex()
}, ra = {
	normal: mi,
	gfm: gi,
	pedantic: _i
}, ia = {
	normal: $i,
	gfm: ta,
	breaks: na,
	pedantic: ea
}, aa = {
	"&": "&amp;",
	"<": "&lt;",
	">": "&gt;",
	"\"": "&quot;",
	"'": "&#39;"
}, oa = (e) => aa[e];
function sa(e, t) {
	if (t) {
		if (Y.escapeTest.test(e)) return e.replace(Y.escapeReplace, oa);
	} else if (Y.escapeTestNoEncode.test(e)) return e.replace(Y.escapeReplaceNoEncode, oa);
	return e;
}
function ca(e) {
	try {
		e = encodeURI(e).replace(Y.percentDecode, "%");
	} catch {
		return null;
	}
	return e;
}
function la(e, t) {
	let n = e.replace(Y.findPipe, (e, t, n) => {
		let r = !1, i = t;
		for (; --i >= 0 && n[i] === "\\";) r = !r;
		return r ? "|" : " |";
	}).split(Y.splitPipe), r = 0;
	if (n[0].trim() || n.shift(), n.length > 0 && !n.at(-1)?.trim() && n.pop(), t) {
		if (n.length > t) n.splice(t);
		else for (; n.length < t;) n.push("");
	}
	for (; r < n.length; r++) n[r] = n[r].trim().replace(Y.slashPipe, "|");
	return n;
}
function ua(e, t, n) {
	let r = e.length;
	if (r === 0) return "";
	let i = 0;
	for (; i < r;) {
		let a = e.charAt(r - i - 1);
		if (a === t && !n) i++;
		else if (a !== t && n) i++;
		else break;
	}
	return e.slice(0, r - i);
}
function da(e) {
	let t = e.split("\n"), n = t.length - 1;
	for (; n >= 0 && Y.blankLine.test(t[n]);) n--;
	return t.length - n <= 2 ? e : t.slice(0, n + 1).join("\n");
}
function fa(e, t) {
	if (e.indexOf(t[1]) === -1) return -1;
	let n = 0;
	for (let r = 0; r < e.length; r++) if (e[r] === "\\") r++;
	else if (e[r] === t[0]) n++;
	else if (e[r] === t[1] && (n--, n < 0)) return r;
	return n > 0 ? -2 : -1;
}
function pa(e, t = 0) {
	let n = t, r = "";
	for (let t of e) if (t === "	") {
		let e = 4 - n % 4;
		r += " ".repeat(e), n += e;
	} else r += t, n++;
	return r;
}
function ma(e, t, n, r, i) {
	let a = t.href, o = t.title || null, s = e[1].replace(i.other.outputLinkReplace, "$1");
	r.state.inLink = !0;
	let c = {
		type: e[0].charAt(0) === "!" ? "image" : "link",
		raw: n,
		href: a,
		title: o,
		text: s,
		tokens: r.inlineTokens(s)
	};
	return r.state.inLink = !1, c;
}
function ha(e, t, n) {
	let r = e.match(n.other.indentCodeCompensation);
	if (r === null) return t;
	let i = r[1];
	return t.split("\n").map((e) => {
		let t = e.match(n.other.beginningSpace);
		if (t === null) return e;
		let [r] = t;
		return r.length >= i.length ? e.slice(i.length) : e;
	}).join("\n");
}
var ga = class {
	options;
	rules;
	lexer;
	constructor(e) {
		this.options = e || Ur;
	}
	space(e) {
		let t = this.rules.block.newline.exec(e);
		if (t && t[0].length > 0) return {
			type: "space",
			raw: t[0]
		};
	}
	code(e) {
		let t = this.rules.block.code.exec(e);
		if (t) {
			let e = this.options.pedantic ? t[0] : da(t[0]);
			return {
				type: "code",
				raw: e,
				codeBlockStyle: "indented",
				text: e.replace(this.rules.other.codeRemoveIndent, "")
			};
		}
	}
	fences(e) {
		let t = this.rules.block.fences.exec(e);
		if (t) {
			let e = t[0], n = ha(e, t[3] || "", this.rules);
			return {
				type: "code",
				raw: e,
				lang: t[2] ? t[2].trim().replace(this.rules.inline.anyPunctuation, "$1") : t[2],
				text: n
			};
		}
	}
	heading(e) {
		let t = this.rules.block.heading.exec(e);
		if (t) {
			let e = t[2].trim();
			if (this.rules.other.endingHash.test(e)) {
				let t = ua(e, "#");
				(this.options.pedantic || !t || this.rules.other.endingSpaceChar.test(t)) && (e = t.trim());
			}
			return {
				type: "heading",
				raw: ua(t[0], "\n"),
				depth: t[1].length,
				text: e,
				tokens: this.lexer.inline(e)
			};
		}
	}
	hr(e) {
		let t = this.rules.block.hr.exec(e);
		if (t) return {
			type: "hr",
			raw: ua(t[0], "\n")
		};
	}
	blockquote(e) {
		let t = this.rules.block.blockquote.exec(e);
		if (t) {
			let e = ua(t[0], "\n").split("\n"), n = "", r = "", i = [];
			for (; e.length > 0;) {
				let t = !1, a = [], o;
				for (o = 0; o < e.length; o++) if (this.rules.other.blockquoteStart.test(e[o])) a.push(e[o]), t = !0;
				else if (!t) a.push(e[o]);
				else break;
				e = e.slice(o);
				let s = a.join("\n"), c = s.replace(this.rules.other.blockquoteSetextReplace, "\n    $1").replace(this.rules.other.blockquoteSetextReplace2, "");
				n = n ? `${n}
${s}` : s, r = r ? `${r}
${c}` : c;
				let l = this.lexer.state.top;
				if (this.lexer.state.top = !0, this.lexer.blockTokens(c, i, !0), this.lexer.state.top = l, e.length === 0) break;
				let u = i.at(-1);
				if (u?.type === "code") break;
				if (u?.type === "blockquote") {
					let t = u, a = e.join("\n"), o = t.raw + "\n" + a.replace(this.rules.other.blockquoteSetextReplace2, ""), s = this.blockquote(o);
					i[i.length - 1] = s, n = `${n}
${a}`, r = r.substring(0, r.length - t.text.length) + s.text;
					break;
				}
				if (u?.type === "list") {
					let t = u, a = t.raw + "\n" + e.join("\n"), o = this.list(a);
					i[i.length - 1] = o, n = n.substring(0, n.length - u.raw.length) + o.raw, r = r.substring(0, r.length - t.raw.length) + o.raw, e = a.substring(i.at(-1).raw.length).split("\n");
					continue;
				}
			}
			return {
				type: "blockquote",
				raw: n,
				tokens: i,
				text: r
			};
		}
	}
	list(e) {
		let t = this.rules.block.list.exec(e);
		if (t) {
			let n = t[1].trim(), r = n.length > 1, i = {
				type: "list",
				raw: "",
				ordered: r,
				start: r ? +n.slice(0, -1) : "",
				loose: !1,
				items: []
			};
			n = r ? `\\d{1,9}\\${n.slice(-1)}` : `\\${n}`, this.options.pedantic && (n = r ? n : "[*+-]");
			let a = this.rules.other.listItemRegex(n), o = !1;
			for (; e;) {
				let n = !1, r = "", s = "";
				if (!(t = a.exec(e)) || this.rules.block.hr.test(e)) break;
				r = t[0], e = e.substring(r.length);
				let c = pa(t[2].split("\n", 1)[0], t[1].length), l = e.split("\n", 1)[0], u = !c.trim(), d = 0;
				if (this.options.pedantic ? (d = 2, s = c.trimStart()) : u ? d = t[1].length + 1 : (d = c.search(this.rules.other.nonSpaceChar), d = d > 4 ? 1 : d, s = c.slice(d), d += t[1].length), u && this.rules.other.blankLine.test(l) && (r += l + "\n", e = e.substring(l.length + 1), n = !0), !n) {
					let t = this.rules.other.nextBulletRegex(d), n = this.rules.other.hrRegex(d), i = this.rules.other.fencesBeginRegex(d), a = this.rules.other.headingBeginRegex(d), o = this.rules.other.htmlBeginRegex(d), f = this.rules.other.blockquoteBeginRegex(d);
					for (; e;) {
						let p = e.split("\n", 1)[0], m;
						if (l = p, this.options.pedantic ? (l = l.replace(this.rules.other.listReplaceNesting, "  "), m = l) : m = l.replace(this.rules.other.tabCharGlobal, "    "), i.test(l) || a.test(l) || o.test(l) || f.test(l) || t.test(l) || n.test(l)) break;
						if (m.search(this.rules.other.nonSpaceChar) >= d || !l.trim()) s += "\n" + m.slice(d);
						else {
							if (u || c.replace(this.rules.other.tabCharGlobal, "    ").search(this.rules.other.nonSpaceChar) >= 4 || i.test(c) || a.test(c) || n.test(c)) break;
							s += "\n" + l;
						}
						u = !l.trim(), r += p + "\n", e = e.substring(p.length + 1), c = m.slice(d);
					}
				}
				i.loose || (o ? i.loose = !0 : this.rules.other.doubleBlankLine.test(r) && (o = !0)), i.items.push({
					type: "list_item",
					raw: r,
					task: !!this.options.gfm && this.rules.other.listIsTask.test(s),
					loose: !1,
					text: s,
					tokens: []
				}), i.raw += r;
			}
			let s = i.items.at(-1);
			if (s) s.raw = s.raw.trimEnd(), s.text = s.text.trimEnd();
			else return;
			i.raw = i.raw.trimEnd();
			for (let e of i.items) if (this.lexer.state.top = !1, e.tokens = this.lexer.blockTokens(e.text, []), !i.loose) {
				let t = e.tokens.filter((e) => e.type === "space");
				i.loose = t.length > 0 && t.some((e) => this.rules.other.anyLine.test(e.raw));
			}
			for (let e of i.items) {
				let t = e.tokens[0];
				if (e.task && (t?.type === "text" || t?.type === "paragraph")) {
					e.text = e.text.replace(this.rules.other.listReplaceTask, ""), t.raw = t.raw.replace(this.rules.other.listReplaceTask, ""), t.text = t.text.replace(this.rules.other.listReplaceTask, "");
					for (let e = this.lexer.inlineQueue.length - 1; e >= 0; e--) if (this.rules.other.listIsTask.test(this.lexer.inlineQueue[e].src)) {
						this.lexer.inlineQueue[e].src = this.lexer.inlineQueue[e].src.replace(this.rules.other.listReplaceTask, "");
						break;
					}
					let n = this.rules.other.listTaskCheckbox.exec(e.raw);
					if (n) {
						let t = {
							type: "checkbox",
							raw: n[0] + " ",
							checked: n[0] !== "[ ]"
						};
						e.checked = t.checked, i.loose ? e.tokens[0] && ["paragraph", "text"].includes(e.tokens[0].type) && "tokens" in e.tokens[0] && e.tokens[0].tokens ? (e.tokens[0].raw = t.raw + e.tokens[0].raw, e.tokens[0].text = t.raw + e.tokens[0].text, e.tokens[0].tokens.unshift(t)) : e.tokens.unshift({
							type: "paragraph",
							raw: t.raw,
							text: t.raw,
							tokens: [t]
						}) : e.tokens.unshift(t);
					}
				} else e.task &&= !1;
			}
			if (i.loose) for (let e of i.items) {
				e.loose = !0;
				for (let t of e.tokens) t.type === "text" && (t.type = "paragraph");
			}
			return i;
		}
	}
	html(e) {
		let t = this.rules.block.html.exec(e);
		if (t) {
			let e = da(t[0]);
			return {
				type: "html",
				block: !0,
				raw: e,
				pre: t[1] === "pre" || t[1] === "script" || t[1] === "style",
				text: e
			};
		}
	}
	def(e) {
		let t = this.rules.block.def.exec(e);
		if (t) {
			let e = t[1].toLowerCase().replace(this.rules.other.multipleSpaceGlobal, " "), n = t[2] ? t[2].replace(this.rules.other.hrefBrackets, "$1").replace(this.rules.inline.anyPunctuation, "$1") : "", r = t[3] ? t[3].substring(1, t[3].length - 1).replace(this.rules.inline.anyPunctuation, "$1") : t[3];
			return {
				type: "def",
				tag: e,
				raw: ua(t[0], "\n"),
				href: n,
				title: r
			};
		}
	}
	table(e) {
		let t = this.rules.block.table.exec(e);
		if (!t || !this.rules.other.tableDelimiter.test(t[2])) return;
		let n = la(t[1]), r = t[2].replace(this.rules.other.tableAlignChars, "").split("|"), i = t[3]?.trim() ? t[3].replace(this.rules.other.tableRowBlankLine, "").split("\n") : [], a = {
			type: "table",
			raw: ua(t[0], "\n"),
			header: [],
			align: [],
			rows: []
		};
		if (n.length === r.length) {
			for (let e of r) this.rules.other.tableAlignRight.test(e) ? a.align.push("right") : this.rules.other.tableAlignCenter.test(e) ? a.align.push("center") : this.rules.other.tableAlignLeft.test(e) ? a.align.push("left") : a.align.push(null);
			for (let e = 0; e < n.length; e++) a.header.push({
				text: n[e],
				tokens: this.lexer.inline(n[e]),
				header: !0,
				align: a.align[e]
			});
			for (let e of i) a.rows.push(la(e, a.header.length).map((e, t) => ({
				text: e,
				tokens: this.lexer.inline(e),
				header: !1,
				align: a.align[t]
			})));
			return a;
		}
	}
	lheading(e) {
		let t = this.rules.block.lheading.exec(e);
		if (t) {
			let e = t[1].trim();
			return {
				type: "heading",
				raw: ua(t[0], "\n"),
				depth: t[2].charAt(0) === "=" ? 1 : 2,
				text: e,
				tokens: this.lexer.inline(e)
			};
		}
	}
	paragraph(e) {
		let t = this.rules.block.paragraph.exec(e);
		if (t) {
			let e = t[1].charAt(t[1].length - 1) === "\n" ? t[1].slice(0, -1) : t[1];
			return {
				type: "paragraph",
				raw: t[0],
				text: e,
				tokens: this.lexer.inline(e)
			};
		}
	}
	text(e) {
		let t = this.rules.block.text.exec(e);
		if (t) return {
			type: "text",
			raw: t[0],
			text: t[0],
			tokens: this.lexer.inline(t[0])
		};
	}
	escape(e) {
		let t = this.rules.inline.escape.exec(e);
		if (t) return {
			type: "escape",
			raw: t[0],
			text: t[1]
		};
	}
	tag(e) {
		let t = this.rules.inline.tag.exec(e);
		if (t) return !this.lexer.state.inLink && this.rules.other.startATag.test(t[0]) ? this.lexer.state.inLink = !0 : this.lexer.state.inLink && this.rules.other.endATag.test(t[0]) && (this.lexer.state.inLink = !1), !this.lexer.state.inRawBlock && this.rules.other.startPreScriptTag.test(t[0]) ? this.lexer.state.inRawBlock = !0 : this.lexer.state.inRawBlock && this.rules.other.endPreScriptTag.test(t[0]) && (this.lexer.state.inRawBlock = !1), {
			type: "html",
			raw: t[0],
			inLink: this.lexer.state.inLink,
			inRawBlock: this.lexer.state.inRawBlock,
			block: !1,
			text: t[0]
		};
	}
	link(e) {
		let t = this.rules.inline.link.exec(e);
		if (t) {
			let e = t[2].trim();
			if (!this.options.pedantic && this.rules.other.startAngleBracket.test(e)) {
				if (!this.rules.other.endAngleBracket.test(e)) return;
				let t = ua(e.slice(0, -1), "\\");
				if ((e.length - t.length) % 2 == 0) return;
			} else {
				let e = fa(t[2], "()");
				if (e === -2) return;
				if (e > -1) {
					let n = (t[0].indexOf("!") === 0 ? 5 : 4) + t[1].length + e;
					t[2] = t[2].substring(0, e), t[0] = t[0].substring(0, n).trim(), t[3] = "";
				}
			}
			let n = t[2], r = "";
			if (this.options.pedantic) {
				let e = this.rules.other.pedanticHrefTitle.exec(n);
				e && (n = e[1], r = e[3]);
			} else r = t[3] ? t[3].slice(1, -1) : "";
			return n = n.trim(), this.rules.other.startAngleBracket.test(n) && (n = this.options.pedantic && !this.rules.other.endAngleBracket.test(e) ? n.slice(1) : n.slice(1, -1)), ma(t, {
				href: n && n.replace(this.rules.inline.anyPunctuation, "$1"),
				title: r && r.replace(this.rules.inline.anyPunctuation, "$1")
			}, t[0], this.lexer, this.rules);
		}
	}
	reflink(e, t) {
		let n;
		if ((n = this.rules.inline.reflink.exec(e)) || (n = this.rules.inline.nolink.exec(e))) {
			let e = t[(n[2] || n[1]).replace(this.rules.other.multipleSpaceGlobal, " ").toLowerCase()];
			if (!e) {
				let e = n[0].charAt(0);
				return {
					type: "text",
					raw: e,
					text: e
				};
			}
			return ma(n, e, n[0], this.lexer, this.rules);
		}
	}
	emStrong(e, t, n = "") {
		let r = this.rules.inline.emStrongLDelim.exec(e);
		if (!(!r || !r[1] && !r[2] && !r[3] && !r[4] || r[4] && n.match(this.rules.other.unicodeAlphaNumeric)) && (!(r[1] || r[3]) || !n || this.rules.inline.punctuation.exec(n))) {
			let i = [...r[0]].length - 1, a, o, s = i, c = 0, l = r[0][0], u = n === l, d = l === "*" ? this.rules.inline.emStrongRDelimAst : this.rules.inline.emStrongRDelimUnd;
			for (d.lastIndex = 0, t = t.slice(-1 * e.length + i); (r = d.exec(t)) !== null;) {
				if (a = r[1] || r[2] || r[3] || r[4] || r[5] || r[6], !a) continue;
				if (o = [...a].length, r[3] || r[4]) {
					s += o;
					continue;
				}
				if (r[5] || r[6]) {
					if (i % 3 && !((i + o) % 3)) {
						c += o;
						continue;
					}
					if (u) break;
				}
				if (s -= o, s > 0) continue;
				o = Math.min(o, o + s + c);
				let t = [...r[0]][0].length, n = e.slice(0, i + r.index + t + o);
				if (Math.min(i, o) % 2) {
					let e = n.slice(1, -1);
					return {
						type: "em",
						raw: n,
						text: e,
						tokens: this.lexer.inlineTokens(e)
					};
				}
				let l = n.slice(2, -2);
				return {
					type: "strong",
					raw: n,
					text: l,
					tokens: this.lexer.inlineTokens(l)
				};
			}
		}
	}
	codespan(e) {
		let t = this.rules.inline.code.exec(e);
		if (t) {
			let e = t[2].replace(this.rules.other.newLineCharGlobal, " "), n = this.rules.other.nonSpaceChar.test(e), r = this.rules.other.startingSpaceChar.test(e) && this.rules.other.endingSpaceChar.test(e);
			return n && r && (e = e.substring(1, e.length - 1)), {
				type: "codespan",
				raw: t[0],
				text: e
			};
		}
	}
	br(e) {
		let t = this.rules.inline.br.exec(e);
		if (t) return {
			type: "br",
			raw: t[0]
		};
	}
	del(e, t, n = "") {
		let r = this.rules.inline.delLDelim.exec(e);
		if (r && (!r[1] || !n || this.rules.inline.punctuation.exec(n))) {
			let n = [...r[0]].length - 1, i, a, o = n, s = this.rules.inline.delRDelim;
			for (s.lastIndex = 0, t = t.slice(-1 * e.length + n); (r = s.exec(t)) !== null;) {
				if (i = r[1] || r[2] || r[3] || r[4] || r[5] || r[6], !i || (a = [...i].length, a !== n)) continue;
				if (r[3] || r[4]) {
					o += a;
					continue;
				}
				if (o -= a, o > 0) continue;
				a = Math.min(a, a + o);
				let t = [...r[0]][0].length, s = e.slice(0, n + r.index + t + a), c = s.slice(n, -n);
				return {
					type: "del",
					raw: s,
					text: c,
					tokens: this.lexer.inlineTokens(c)
				};
			}
		}
	}
	autolink(e) {
		let t = this.rules.inline.autolink.exec(e);
		if (t) {
			let e, n;
			return t[2] === "@" ? (e = t[1], n = "mailto:" + e) : (e = t[1], n = e), {
				type: "link",
				raw: t[0],
				text: e,
				href: n,
				tokens: [{
					type: "text",
					raw: e,
					text: e
				}]
			};
		}
	}
	url(e) {
		let t;
		if (t = this.rules.inline.url.exec(e)) {
			let e, n;
			if (t[2] === "@") e = t[0], n = "mailto:" + e;
			else {
				let r;
				do
					r = t[0], t[0] = this.rules.inline._backpedal.exec(t[0])?.[0] ?? "";
				while (r !== t[0]);
				e = t[0], n = t[1] === "www." ? "http://" + t[0] : t[0];
			}
			return {
				type: "link",
				raw: t[0],
				text: e,
				href: n,
				tokens: [{
					type: "text",
					raw: e,
					text: e
				}]
			};
		}
	}
	inlineText(e) {
		let t = this.rules.inline.text.exec(e);
		if (t) {
			let e = this.lexer.state.inRawBlock;
			return {
				type: "text",
				raw: t[0],
				text: t[0],
				escaped: e
			};
		}
	}
}, _a = class e {
	tokens;
	options;
	state;
	inlineQueue;
	tokenizer;
	constructor(e) {
		this.tokens = [], this.tokens.links = Object.create(null), this.options = e || Ur, this.options.tokenizer = this.options.tokenizer || new ga(), this.tokenizer = this.options.tokenizer, this.tokenizer.options = this.options, this.tokenizer.lexer = this, this.inlineQueue = [], this.state = {
			inLink: !1,
			inRawBlock: !1,
			top: !0
		};
		let t = {
			other: Y,
			block: ra.normal,
			inline: ia.normal
		};
		this.options.pedantic ? (t.block = ra.pedantic, t.inline = ia.pedantic) : this.options.gfm && (t.block = ra.gfm, t.inline = this.options.breaks ? ia.breaks : ia.gfm), this.tokenizer.rules = t;
	}
	static get rules() {
		return {
			block: ra,
			inline: ia
		};
	}
	static lex(t, n) {
		return new e(n).lex(t);
	}
	static lexInline(t, n) {
		return new e(n).inlineTokens(t);
	}
	lex(e) {
		e = e.replace(Y.carriageReturn, "\n"), this.blockTokens(e, this.tokens);
		for (let e = 0; e < this.inlineQueue.length; e++) {
			let t = this.inlineQueue[e];
			this.inlineTokens(t.src, t.tokens);
		}
		return this.inlineQueue = [], this.tokens;
	}
	blockTokens(e, t = [], n = !1) {
		this.tokenizer.lexer = this, this.options.pedantic && (e = e.replace(Y.tabCharGlobal, "    ").replace(Y.spaceLine, ""));
		let r = 1 / 0;
		for (; e;) {
			if (e.length < r) r = e.length;
			else {
				this.infiniteLoopError(e.charCodeAt(0));
				break;
			}
			let i;
			if (this.options.extensions?.block?.some((n) => (i = n.call({ lexer: this }, e, t)) ? (e = e.substring(i.raw.length), t.push(i), !0) : !1)) continue;
			if (i = this.tokenizer.space(e)) {
				e = e.substring(i.raw.length);
				let n = t.at(-1);
				i.raw.length === 1 && n !== void 0 ? n.raw += "\n" : t.push(i);
				continue;
			}
			if (i = this.tokenizer.code(e)) {
				e = e.substring(i.raw.length);
				let n = t.at(-1);
				n?.type === "paragraph" || n?.type === "text" ? (n.raw += (n.raw.endsWith("\n") ? "" : "\n") + i.raw, n.text += "\n" + i.text, this.inlineQueue.at(-1).src = n.text) : t.push(i);
				continue;
			}
			if (i = this.tokenizer.fences(e)) {
				e = e.substring(i.raw.length), t.push(i);
				continue;
			}
			if (i = this.tokenizer.heading(e)) {
				e = e.substring(i.raw.length), t.push(i);
				continue;
			}
			if (i = this.tokenizer.hr(e)) {
				e = e.substring(i.raw.length), t.push(i);
				continue;
			}
			if (i = this.tokenizer.blockquote(e)) {
				e = e.substring(i.raw.length), t.push(i);
				continue;
			}
			if (i = this.tokenizer.list(e)) {
				e = e.substring(i.raw.length), t.push(i);
				continue;
			}
			if (i = this.tokenizer.html(e)) {
				e = e.substring(i.raw.length), t.push(i);
				continue;
			}
			if (i = this.tokenizer.def(e)) {
				e = e.substring(i.raw.length);
				let n = t.at(-1);
				n?.type === "paragraph" || n?.type === "text" ? (n.raw += (n.raw.endsWith("\n") ? "" : "\n") + i.raw, n.text += "\n" + i.raw, this.inlineQueue.at(-1).src = n.text) : this.tokens.links[i.tag] || (this.tokens.links[i.tag] = {
					href: i.href,
					title: i.title
				}, t.push(i));
				continue;
			}
			if (i = this.tokenizer.table(e)) {
				e = e.substring(i.raw.length), t.push(i);
				continue;
			}
			if (i = this.tokenizer.lheading(e)) {
				e = e.substring(i.raw.length), t.push(i);
				continue;
			}
			let a = e;
			if (this.options.extensions?.startBlock) {
				let t = 1 / 0, n = e.slice(1), r;
				this.options.extensions.startBlock.forEach((e) => {
					r = e.call({ lexer: this }, n), typeof r == "number" && r >= 0 && (t = Math.min(t, r));
				}), t < 1 / 0 && t >= 0 && (a = e.substring(0, t + 1));
			}
			if (this.state.top && (i = this.tokenizer.paragraph(a))) {
				let r = t.at(-1);
				n && r?.type === "paragraph" ? (r.raw += (r.raw.endsWith("\n") ? "" : "\n") + i.raw, r.text += "\n" + i.text, this.inlineQueue.pop(), this.inlineQueue.at(-1).src = r.text) : t.push(i), n = a.length !== e.length, e = e.substring(i.raw.length);
				continue;
			}
			if (i = this.tokenizer.text(e)) {
				e = e.substring(i.raw.length);
				let n = t.at(-1);
				n?.type === "text" ? (n.raw += (n.raw.endsWith("\n") ? "" : "\n") + i.raw, n.text += "\n" + i.text, this.inlineQueue.pop(), this.inlineQueue.at(-1).src = n.text) : t.push(i);
				continue;
			}
			if (e) {
				this.infiniteLoopError(e.charCodeAt(0));
				break;
			}
		}
		return this.state.top = !0, t;
	}
	inline(e, t = []) {
		return this.inlineQueue.push({
			src: e,
			tokens: t
		}), t;
	}
	inlineTokens(e, t = []) {
		this.tokenizer.lexer = this;
		let n = e;
		if (this.tokens.links) {
			let e = Object.keys(this.tokens.links);
			e.length > 0 && (n = n.replace(this.tokenizer.rules.inline.reflinkSearch, (t) => e.includes(t.slice(t.lastIndexOf("[") + 1, -1)) ? "[" + "a".repeat(t.length - 2) + "]" : t));
		}
		n = n.replace(this.tokenizer.rules.inline.anyPunctuation, (e) => "+".repeat(e.length)), n = n.replace(this.tokenizer.rules.inline.blockSkip, (e, t, n) => {
			let r = n ? n.length : 0;
			return e.slice(0, r) + "[" + "a".repeat(e.length - r - 2) + "]";
		}), n = this.options.hooks?.emStrongMask?.call({ lexer: this }, n) ?? n;
		let r = !1, i = "", a = 1 / 0;
		for (; e;) {
			if (e.length < a) a = e.length;
			else {
				this.infiniteLoopError(e.charCodeAt(0));
				break;
			}
			r || (i = ""), r = !1;
			let o;
			if (this.options.extensions?.inline?.some((n) => (o = n.call({ lexer: this }, e, t)) ? (e = e.substring(o.raw.length), t.push(o), !0) : !1)) continue;
			if (o = this.tokenizer.escape(e)) {
				e = e.substring(o.raw.length), t.push(o);
				continue;
			}
			if (o = this.tokenizer.tag(e)) {
				e = e.substring(o.raw.length), t.push(o);
				continue;
			}
			if (o = this.tokenizer.link(e)) {
				e = e.substring(o.raw.length), t.push(o);
				continue;
			}
			if (o = this.tokenizer.reflink(e, this.tokens.links)) {
				e = e.substring(o.raw.length);
				let n = t.at(-1);
				o.type === "text" && n?.type === "text" ? (n.raw += o.raw, n.text += o.text) : t.push(o);
				continue;
			}
			if (o = this.tokenizer.emStrong(e, n, i)) {
				e = e.substring(o.raw.length), t.push(o);
				continue;
			}
			if (o = this.tokenizer.codespan(e)) {
				e = e.substring(o.raw.length), t.push(o);
				continue;
			}
			if (o = this.tokenizer.br(e)) {
				e = e.substring(o.raw.length), t.push(o);
				continue;
			}
			if (o = this.tokenizer.del(e, n, i)) {
				e = e.substring(o.raw.length), t.push(o);
				continue;
			}
			if (o = this.tokenizer.autolink(e)) {
				e = e.substring(o.raw.length), t.push(o);
				continue;
			}
			if (!this.state.inLink && (o = this.tokenizer.url(e))) {
				e = e.substring(o.raw.length), t.push(o);
				continue;
			}
			let s = e;
			if (this.options.extensions?.startInline) {
				let t = 1 / 0, n = e.slice(1), r;
				this.options.extensions.startInline.forEach((e) => {
					r = e.call({ lexer: this }, n), typeof r == "number" && r >= 0 && (t = Math.min(t, r));
				}), t < 1 / 0 && t >= 0 && (s = e.substring(0, t + 1));
			}
			if (o = this.tokenizer.inlineText(s)) {
				e = e.substring(o.raw.length), o.raw.slice(-1) !== "_" && (i = o.raw.slice(-1)), r = !0;
				let n = t.at(-1);
				n?.type === "text" ? (n.raw += o.raw, n.text += o.text) : t.push(o);
				continue;
			}
			if (e) {
				this.infiniteLoopError(e.charCodeAt(0));
				break;
			}
		}
		return t;
	}
	infiniteLoopError(e) {
		let t = "Infinite loop on byte: " + e;
		if (this.options.silent) console.error(t);
		else throw Error(t);
	}
}, va = class {
	options;
	parser;
	constructor(e) {
		this.options = e || Ur;
	}
	space(e) {
		return "";
	}
	code({ text: e, lang: t, escaped: n }) {
		let r = (t || "").match(Y.notSpaceStart)?.[0], i = e.replace(Y.endingNewline, "") + "\n";
		return r ? "<pre><code class=\"language-" + sa(r) + "\">" + (n ? i : sa(i, !0)) + "</code></pre>\n" : "<pre><code>" + (n ? i : sa(i, !0)) + "</code></pre>\n";
	}
	blockquote({ tokens: e }) {
		return `<blockquote>
${this.parser.parse(e)}</blockquote>
`;
	}
	html({ text: e }) {
		return e;
	}
	def(e) {
		return "";
	}
	heading({ tokens: e, depth: t }) {
		return `<h${t}>${this.parser.parseInline(e)}</h${t}>
`;
	}
	hr(e) {
		return "<hr>\n";
	}
	list(e) {
		let t = e.ordered, n = e.start, r = "";
		for (let t = 0; t < e.items.length; t++) {
			let n = e.items[t];
			r += this.listitem(n);
		}
		let i = t ? "ol" : "ul", a = t && n !== 1 ? " start=\"" + n + "\"" : "";
		return "<" + i + a + ">\n" + r + "</" + i + ">\n";
	}
	listitem(e) {
		return `<li>${this.parser.parse(e.tokens)}</li>
`;
	}
	checkbox({ checked: e }) {
		return "<input " + (e ? "checked=\"\" " : "") + "disabled=\"\" type=\"checkbox\"> ";
	}
	paragraph({ tokens: e }) {
		return `<p>${this.parser.parseInline(e)}</p>
`;
	}
	table(e) {
		let t = "", n = "";
		for (let t = 0; t < e.header.length; t++) n += this.tablecell(e.header[t]);
		t += this.tablerow({ text: n });
		let r = "";
		for (let t = 0; t < e.rows.length; t++) {
			let i = e.rows[t];
			n = "";
			for (let e = 0; e < i.length; e++) n += this.tablecell(i[e]);
			r += this.tablerow({ text: n });
		}
		return r &&= `<tbody>${r}</tbody>`, "<table>\n<thead>\n" + t + "</thead>\n" + r + "</table>\n";
	}
	tablerow({ text: e }) {
		return `<tr>
${e}</tr>
`;
	}
	tablecell(e) {
		let t = this.parser.parseInline(e.tokens), n = e.header ? "th" : "td";
		return (e.align ? `<${n} align="${e.align}">` : `<${n}>`) + t + `</${n}>
`;
	}
	strong({ tokens: e }) {
		return `<strong>${this.parser.parseInline(e)}</strong>`;
	}
	em({ tokens: e }) {
		return `<em>${this.parser.parseInline(e)}</em>`;
	}
	codespan({ text: e }) {
		return `<code>${sa(e, !0)}</code>`;
	}
	br(e) {
		return "<br>";
	}
	del({ tokens: e }) {
		return `<del>${this.parser.parseInline(e)}</del>`;
	}
	link({ href: e, title: t, tokens: n }) {
		let r = this.parser.parseInline(n), i = ca(e);
		if (i === null) return r;
		e = i;
		let a = "<a href=\"" + e + "\"";
		return t && (a += " title=\"" + sa(t) + "\""), a += ">" + r + "</a>", a;
	}
	image({ href: e, title: t, text: n, tokens: r }) {
		r && (n = this.parser.parseInline(r, this.parser.textRenderer));
		let i = ca(e);
		if (i === null) return sa(n);
		e = i;
		let a = `<img src="${e}" alt="${sa(n)}"`;
		return t && (a += ` title="${sa(t)}"`), a += ">", a;
	}
	text(e) {
		return "tokens" in e && e.tokens ? this.parser.parseInline(e.tokens) : "escaped" in e && e.escaped ? e.text : sa(e.text);
	}
}, ya = class {
	strong({ text: e }) {
		return e;
	}
	em({ text: e }) {
		return e;
	}
	codespan({ text: e }) {
		return e;
	}
	del({ text: e }) {
		return e;
	}
	html({ text: e }) {
		return e;
	}
	text({ text: e }) {
		return e;
	}
	link({ text: e }) {
		return "" + e;
	}
	image({ text: e }) {
		return "" + e;
	}
	br() {
		return "";
	}
	checkbox({ raw: e }) {
		return e;
	}
}, ba = class e {
	options;
	renderer;
	textRenderer;
	constructor(e) {
		this.options = e || Ur, this.options.renderer = this.options.renderer || new va(), this.renderer = this.options.renderer, this.renderer.options = this.options, this.renderer.parser = this, this.textRenderer = new ya();
	}
	static parse(t, n) {
		return new e(n).parse(t);
	}
	static parseInline(t, n) {
		return new e(n).parseInline(t);
	}
	parse(e) {
		this.renderer.parser = this;
		let t = "";
		for (let n = 0; n < e.length; n++) {
			let r = e[n];
			if (this.options.extensions?.renderers?.[r.type]) {
				let e = r, n = this.options.extensions.renderers[e.type].call({ parser: this }, e);
				if (n !== !1 || ![
					"space",
					"hr",
					"heading",
					"code",
					"table",
					"blockquote",
					"list",
					"checkbox",
					"html",
					"def",
					"paragraph",
					"text"
				].includes(e.type)) {
					t += n || "";
					continue;
				}
			}
			let i = r;
			switch (i.type) {
				case "space":
					t += this.renderer.space(i);
					break;
				case "hr":
					t += this.renderer.hr(i);
					break;
				case "heading":
					t += this.renderer.heading(i);
					break;
				case "code":
					t += this.renderer.code(i);
					break;
				case "table":
					t += this.renderer.table(i);
					break;
				case "blockquote":
					t += this.renderer.blockquote(i);
					break;
				case "list":
					t += this.renderer.list(i);
					break;
				case "checkbox":
					t += this.renderer.checkbox(i);
					break;
				case "html":
					t += this.renderer.html(i);
					break;
				case "def":
					t += this.renderer.def(i);
					break;
				case "paragraph":
					t += this.renderer.paragraph(i);
					break;
				case "text":
					t += this.renderer.text(i);
					break;
				default: {
					let e = "Token with \"" + i.type + "\" type was not found.";
					if (this.options.silent) return console.error(e), "";
					throw Error(e);
				}
			}
		}
		return t;
	}
	parseInline(e, t = this.renderer) {
		this.renderer.parser = this;
		let n = "";
		for (let r = 0; r < e.length; r++) {
			let i = e[r];
			if (this.options.extensions?.renderers?.[i.type]) {
				let e = this.options.extensions.renderers[i.type].call({ parser: this }, i);
				if (e !== !1 || ![
					"escape",
					"html",
					"link",
					"image",
					"checkbox",
					"strong",
					"em",
					"codespan",
					"br",
					"del",
					"text"
				].includes(i.type)) {
					n += e || "";
					continue;
				}
			}
			let a = i;
			switch (a.type) {
				case "escape":
					n += t.text(a);
					break;
				case "html":
					n += t.html(a);
					break;
				case "link":
					n += t.link(a);
					break;
				case "image":
					n += t.image(a);
					break;
				case "checkbox":
					n += t.checkbox(a);
					break;
				case "strong":
					n += t.strong(a);
					break;
				case "em":
					n += t.em(a);
					break;
				case "codespan":
					n += t.codespan(a);
					break;
				case "br":
					n += t.br(a);
					break;
				case "del":
					n += t.del(a);
					break;
				case "text":
					n += t.text(a);
					break;
				default: {
					let e = "Token with \"" + a.type + "\" type was not found.";
					if (this.options.silent) return console.error(e), "";
					throw Error(e);
				}
			}
		}
		return n;
	}
}, xa = class {
	options;
	block;
	constructor(e) {
		this.options = e || Ur;
	}
	static passThroughHooks = /* @__PURE__ */ new Set([
		"preprocess",
		"postprocess",
		"processAllTokens",
		"emStrongMask"
	]);
	static passThroughHooksRespectAsync = /* @__PURE__ */ new Set([
		"preprocess",
		"postprocess",
		"processAllTokens"
	]);
	preprocess(e) {
		return e;
	}
	postprocess(e) {
		return e;
	}
	processAllTokens(e) {
		return e;
	}
	emStrongMask(e) {
		return e;
	}
	provideLexer(e = this.block) {
		return e ? _a.lex : _a.lexInline;
	}
	provideParser(e = this.block) {
		return e ? ba.parse : ba.parseInline;
	}
}, Sa = class {
	defaults = Hr();
	options = this.setOptions;
	parse = this.parseMarkdown(!0);
	parseInline = this.parseMarkdown(!1);
	Parser = ba;
	Renderer = va;
	TextRenderer = ya;
	Lexer = _a;
	Tokenizer = ga;
	Hooks = xa;
	constructor(...e) {
		this.use(...e);
	}
	walkTokens(e, t) {
		let n = [];
		for (let r of e) switch (n = n.concat(t.call(this, r)), r.type) {
			case "table": {
				let e = r;
				for (let r of e.header) n = n.concat(this.walkTokens(r.tokens, t));
				for (let r of e.rows) for (let e of r) n = n.concat(this.walkTokens(e.tokens, t));
				break;
			}
			case "list": {
				let e = r;
				n = n.concat(this.walkTokens(e.items, t));
				break;
			}
			default: {
				let e = r;
				this.defaults.extensions?.childTokens?.[e.type] ? this.defaults.extensions.childTokens[e.type].forEach((r) => {
					let i = e[r].flat(1 / 0);
					n = n.concat(this.walkTokens(i, t));
				}) : e.tokens && (n = n.concat(this.walkTokens(e.tokens, t)));
			}
		}
		return n;
	}
	use(...e) {
		let t = this.defaults.extensions || {
			renderers: {},
			childTokens: {}
		};
		return e.forEach((e) => {
			let n = { ...e };
			if (n.async = this.defaults.async || n.async || !1, e.extensions && (e.extensions.forEach((e) => {
				if (!e.name) throw Error("extension name required");
				if ("renderer" in e) {
					let n = t.renderers[e.name];
					n ? t.renderers[e.name] = function(...t) {
						let r = e.renderer.apply(this, t);
						return r === !1 && (r = n.apply(this, t)), r;
					} : t.renderers[e.name] = e.renderer;
				}
				if ("tokenizer" in e) {
					if (!e.level || e.level !== "block" && e.level !== "inline") throw Error("extension level must be 'block' or 'inline'");
					let n = t[e.level];
					n ? n.unshift(e.tokenizer) : t[e.level] = [e.tokenizer], e.start && (e.level === "block" ? t.startBlock ? t.startBlock.push(e.start) : t.startBlock = [e.start] : e.level === "inline" && (t.startInline ? t.startInline.push(e.start) : t.startInline = [e.start]));
				}
				"childTokens" in e && e.childTokens && (t.childTokens[e.name] = e.childTokens);
			}), n.extensions = t), e.renderer) {
				let t = this.defaults.renderer || new va(this.defaults);
				for (let n in e.renderer) {
					if (!(n in t)) throw Error(`renderer '${n}' does not exist`);
					if (["options", "parser"].includes(n)) continue;
					let r = n, i = e.renderer[r], a = t[r];
					t[r] = (...e) => {
						let n = i.apply(t, e);
						return n === !1 && (n = a.apply(t, e)), n || "";
					};
				}
				n.renderer = t;
			}
			if (e.tokenizer) {
				let t = this.defaults.tokenizer || new ga(this.defaults);
				for (let n in e.tokenizer) {
					if (!(n in t)) throw Error(`tokenizer '${n}' does not exist`);
					if ([
						"options",
						"rules",
						"lexer"
					].includes(n)) continue;
					let r = n, i = e.tokenizer[r], a = t[r];
					t[r] = (...e) => {
						let n = i.apply(t, e);
						return n === !1 && (n = a.apply(t, e)), n;
					};
				}
				n.tokenizer = t;
			}
			if (e.hooks) {
				let t = this.defaults.hooks || new xa();
				for (let n in e.hooks) {
					if (!(n in t)) throw Error(`hook '${n}' does not exist`);
					if (["options", "block"].includes(n)) continue;
					let r = n, i = e.hooks[r], a = t[r];
					t[r] = xa.passThroughHooks.has(n) ? (e) => {
						if (this.defaults.async && xa.passThroughHooksRespectAsync.has(n)) return (async () => {
							let n = await i.call(t, e);
							return a.call(t, n);
						})();
						let r = i.call(t, e);
						return a.call(t, r);
					} : (...e) => {
						if (this.defaults.async) return (async () => {
							let n = await i.apply(t, e);
							return n === !1 && (n = await a.apply(t, e)), n;
						})();
						let n = i.apply(t, e);
						return n === !1 && (n = a.apply(t, e)), n;
					};
				}
				n.hooks = t;
			}
			if (e.walkTokens) {
				let t = this.defaults.walkTokens, r = e.walkTokens;
				n.walkTokens = function(e) {
					let n = [];
					return n.push(r.call(this, e)), t && (n = n.concat(t.call(this, e))), n;
				};
			}
			this.defaults = {
				...this.defaults,
				...n
			};
		}), this;
	}
	setOptions(e) {
		return this.defaults = {
			...this.defaults,
			...e
		}, this;
	}
	lexer(e, t) {
		return _a.lex(e, t ?? this.defaults);
	}
	parser(e, t) {
		return ba.parse(e, t ?? this.defaults);
	}
	parseMarkdown(e) {
		return (t, n) => {
			let r = { ...n }, i = {
				...this.defaults,
				...r
			}, a = this.onError(!!i.silent, !!i.async);
			if (this.defaults.async === !0 && r.async === !1) return a(/* @__PURE__ */ Error("marked(): The async option was set to true by an extension. Remove async: false from the parse options object to return a Promise."));
			if (typeof t > "u" || t === null) return a(/* @__PURE__ */ Error("marked(): input parameter is undefined or null"));
			if (typeof t != "string") return a(/* @__PURE__ */ Error("marked(): input parameter is of type " + Object.prototype.toString.call(t) + ", string expected"));
			if (i.hooks && (i.hooks.options = i, i.hooks.block = e), i.async) return (async () => {
				let n = i.hooks ? await i.hooks.preprocess(t) : t, r = await (i.hooks ? await i.hooks.provideLexer(e) : e ? _a.lex : _a.lexInline)(n, i), a = i.hooks ? await i.hooks.processAllTokens(r) : r;
				i.walkTokens && await Promise.all(this.walkTokens(a, i.walkTokens));
				let o = await (i.hooks ? await i.hooks.provideParser(e) : e ? ba.parse : ba.parseInline)(a, i);
				return i.hooks ? await i.hooks.postprocess(o) : o;
			})().catch(a);
			try {
				i.hooks && (t = i.hooks.preprocess(t));
				let n = (i.hooks ? i.hooks.provideLexer(e) : e ? _a.lex : _a.lexInline)(t, i);
				i.hooks && (n = i.hooks.processAllTokens(n)), i.walkTokens && this.walkTokens(n, i.walkTokens);
				let r = (i.hooks ? i.hooks.provideParser(e) : e ? ba.parse : ba.parseInline)(n, i);
				return i.hooks && (r = i.hooks.postprocess(r)), r;
			} catch (e) {
				return a(e);
			}
		};
	}
	onError(e, t) {
		return (n) => {
			if (n.message += "\nPlease report this to https://github.com/markedjs/marked.", e) {
				let e = "<p>An error occurred:</p><pre>" + sa(n.message + "", !0) + "</pre>";
				return t ? Promise.resolve(e) : e;
			}
			if (t) return Promise.reject(n);
			throw n;
		};
	}
}, Ca = new Sa();
function X(e, t) {
	return Ca.parse(e, t);
}
X.options = X.setOptions = function(e) {
	return Ca.setOptions(e), X.defaults = Ca.defaults, Wr(X.defaults), X;
}, X.getDefaults = Hr, X.defaults = Ur;
function wa(...e) {
	return Ca.use(...e), X.defaults = Ca.defaults, Wr(X.defaults), X;
}
X.use = wa, X.walkTokens = function(e, t) {
	return Ca.walkTokens(e, t);
}, X.parseInline = Ca.parseInline, X.Parser = ba, X.parser = ba.parse, X.Renderer = va, X.TextRenderer = ya, X.Lexer = _a, X.lexer = _a.lex, X.Tokenizer = ga, X.Hooks = xa, X.parse = X, X.options, X.setOptions, X.walkTokens, X.parseInline, ba.parse, _a.lex;
//#endregion
//#region src/presentation.ts
var Ta = {
	accept: "Continue",
	addContext: "Add context",
	agentName: (e) => e ? `${Ea(e)} Agent` : "Agent",
	agentOngoing: "Ongoing",
	agentCompleted: "Completed",
	agentFailed: "Failed",
	agentCancelled: "Cancelled",
	agentBackground: "Started in background",
	agentObserved: (e) => `Observed ${e}`,
	assistantName: "Assistant",
	authRequired: "Authentication required",
	binaryChange: "Binary or structural change",
	cancel: "Cancel",
	changedFiles: "Changed files",
	close: "Close",
	commands: "Commands",
	composerPlaceholder: "Ask anything…",
	copied: "Copied",
	copy: "Copy",
	contextInjection: "Context injection",
	contextSelection: "Context for next prompt",
	contextTruncated: (e) => `Context display truncated (${e.toLocaleString()} characters total).`,
	decline: "Decline",
	deleteSession: "Delete session",
	emptyDescription: "Messages, tool activity, and plans will appear here.",
	emptyTitle: "Start a conversation",
	error: "Something went wrong",
	finish: "I've finished",
	historyGap: "Earlier messages are unavailable for this session.",
	historyGapTitle: "Partial history",
	loadMore: "Load more",
	newChat: "New chat",
	noSessions: "No previous sessions",
	openLink: "Open link",
	openChildSession: "Open child session",
	permission: "Permission required",
	pendingInteractions: (e) => `${e} pending ${e === 1 ? "interaction" : "interactions"}`,
	plan: "Plan",
	retry: "Retry",
	removeContext: (e) => `Remove context: ${e}`,
	resource: "Resource",
	scrollToLatest: "Scroll to latest message",
	send: "Send",
	sessionAge: (e, t) => t === "now" ? "now" : `${e}${{
		minute: "m",
		hour: "h",
		day: "d",
		month: "mo",
		year: "y"
	}[t]}`,
	sessionActions: (e) => `Actions for ${e}`,
	sessionPhase: (e) => Ea(e),
	sessionUntitled: "Untitled session",
	sessions: "Sessions",
	stop: "Stop",
	thinking: "Thinking",
	terminalOutputInActivity: "Terminal output is shown in the activity stream.",
	tool: "Tool",
	toolCollapseLines: "Show less",
	toolExpandLines: (e) => `... more ${e.toLocaleString()} ${e === 1 ? "line" : "lines"}`,
	toolInput: "Input",
	toolNoOutput: "No output",
	toolOutput: "Output",
	toolResult: "tool result",
	unsupportedContent: (e) => `Unsupported agent content: ${e}`,
	unsafeResourceLink: "unsafe resource link",
	usage: (e, t) => `${Da(e)} / ${Da(t)}`,
	you: "You",
	confirmDeleteSession: (e) => `Delete “${e}”?`,
	backToSession: (e) => `Back to ${e}`
};
function Ea(e) {
	return e.replaceAll(/[_-]+/g, " ").trim().replaceAll(/(^|\s)\S/g, (e) => e.toUpperCase());
}
function Da(e) {
	return e < 0xe8d4a51000 ? e.toLocaleString() : e.toExponential(2);
}
//#endregion
//#region src/react/clipboard.ts
var Oa = 1e3;
function ka(e) {
	let [t, n] = F(!1), r = L(!1), i = L(void 0), a = L(0);
	return I(() => (a.current += 1, r.current = !1, n(!1), i.current !== void 0 && (window.clearTimeout(i.current), i.current = void 0), () => {
		a.current += 1, r.current = !1, i.current !== void 0 && (window.clearTimeout(i.current), i.current = void 0);
	}), [e]), {
		copied: t,
		copy: nt((o) => {
			if (!e || t || r.current) return;
			let s = a.current;
			r.current = !0, Aa(e, o).then((e) => {
				s === a.current && (r.current = !1, e && (n(!0), i.current = window.setTimeout(() => {
					i.current = void 0, n(!1);
				}, Oa)));
			});
		}, [t, e])
	};
}
async function Aa(e, t) {
	if (navigator.clipboard?.writeText) try {
		return await navigator.clipboard.writeText(e), !0;
	} catch {
		return !1;
	}
	let n = typeof document.execCommand == "function" ? document.execCommand.bind(document) : void 0;
	if (!n) return !1;
	let r = document.createElement("textarea");
	r.value = e, r.setAttribute("readonly", ""), r.style.position = "fixed", r.style.left = "-9999px", (t.closest(".pretty-aui") ?? t.parentElement ?? document.documentElement).appendChild(r), r.select();
	try {
		return n("copy");
	} catch {
		return !1;
	} finally {
		r.remove();
	}
}
//#endregion
//#region node_modules/.pnpm/preact@10.29.8/node_modules/preact/jsx-runtime/dist/jsxRuntime.module.js
var ja = 0;
Array.isArray;
function Z(e, t, n, r, i, a) {
	t ||= {};
	var o, s, c = t;
	if ("ref" in c) for (s in c = {}, t) s == "ref" ? o = t[s] : c[s] = t[s];
	var l = {
		type: e,
		props: c,
		key: n,
		ref: o,
		__k: null,
		__: null,
		__b: 0,
		__e: null,
		__c: null,
		constructor: void 0,
		__v: --ja,
		__i: -1,
		__u: 0,
		__source: i,
		__self: a
	};
	if (typeof e == "function" && (o = e.defaultProps)) for (s in o) c[s] === void 0 && (c[s] = o[s]);
	return E.vnode && E.vnode(l), l;
}
//#endregion
//#region src/react/MessageActions.tsx
var Ma = new Intl.DateTimeFormat(void 0, {
	month: "short",
	day: "numeric"
}), Na = new Intl.DateTimeFormat(void 0, {
	year: "numeric",
	month: "short",
	day: "numeric"
});
function Pa({ content: e, timestamp: t, clock: n, labels: r }) {
	let i = Ba(), { copied: a, copy: o } = ka(Ia(e)), s = t !== void 0 && Number.isFinite(t) && t >= 0 && !Number.isNaN(new Date(t).valueOf()) ? t : void 0, c = s === void 0 ? null : /* @__PURE__ */ Z("time", {
		className: `paui-message__time paui-message__time--${n}`,
		dateTime: new Date(s).toISOString(),
		children: Fa(s, i)
	}), l = a ? r.copied : r.copy;
	return /* @__PURE__ */ Z("div", {
		className: "paui-message__actions",
		"data-pretty-aui-slot": "message-actions",
		"data-clock": n,
		children: [
			n === "start" ? c : null,
			/* @__PURE__ */ Z("button", {
				className: "paui-message__action",
				type: "button",
				"aria-label": l,
				title: l,
				onClick: (e) => o(e.currentTarget),
				children: Z(a ? Ja : qa, {})
			}),
			n === "end" ? c : null
		]
	});
}
function Fa(e, t = Date.now()) {
	let n = new Date(e), r = new Date(t), i = `${Ga(n.getHours())}:${Ga(n.getMinutes())}`, a = n.getFullYear() === r.getFullYear();
	return a && n.getMonth() === r.getMonth() && n.getDate() === r.getDate() ? i : `${a ? Ma.format(n) : Na.format(n)} ${i}`;
}
function Ia(e) {
	return e.flatMap((e) => e.type === "text" && typeof e.text == "string" ? [e.text] : []).join("");
}
var La = Ua(Date.now()), Ra, za = /* @__PURE__ */ new Set();
function Ba() {
	return pt(Va, () => La, () => La);
}
function Va(e) {
	za.add(e);
	let t = Ua(Date.now());
	if (t !== La) {
		La = t;
		for (let e of za) e();
	}
	return za.size === 1 && Ha(), () => {
		za.delete(e), !za.size && Ra !== void 0 && (window.clearTimeout(Ra), Ra = void 0);
	};
}
function Ha() {
	Ra !== void 0 && window.clearTimeout(Ra);
	let e = Date.now();
	Ra = window.setTimeout(() => {
		Ra = void 0, La = Ua(Date.now());
		for (let e of za) e();
		za.size && Ha();
	}, Wa(e));
}
function Ua(e) {
	let t = new Date(e);
	return t.setHours(0, 0, 0, 0), t.getTime();
}
function Wa(e) {
	let t = new Date(e);
	return t.setHours(24, 0, 0, 0), Math.max(1, t.getTime() - e);
}
function Ga(e) {
	return String(e).padStart(2, "0");
}
function Ka({ children: e }) {
	return /* @__PURE__ */ Z("svg", {
		viewBox: "0 0 16 16",
		"aria-hidden": "true",
		focusable: "false",
		children: e
	});
}
function qa() {
	return /* @__PURE__ */ Z(Ka, { children: [/* @__PURE__ */ Z("rect", {
		x: "2.5",
		y: "4.5",
		width: "9",
		height: "9",
		rx: "2"
	}), /* @__PURE__ */ Z("path", { d: "M5 4V3.5a2 2 0 0 1 2-2h5.5a2 2 0 0 1 2 2V9a2 2 0 0 1-2 2H12" })] });
}
function Ja() {
	return /* @__PURE__ */ Z(Ka, { children: /* @__PURE__ */ Z("path", { d: "m3 8.25 3.15 3.15L13 4.55" }) });
}
//#endregion
//#region src/react/tool-block-model.ts
var Ya = 1e5;
function Xa(e) {
	return eo(e) ?? Qa(e) ?? $a(e) ?? to(e);
}
function Za(e) {
	return (typeof e == "string" ? e : (() => {
		try {
			return JSON.stringify(e, null, 2) ?? String(e);
		} catch {
			return String(e);
		}
	})()).slice(0, Ya);
}
function Qa(e) {
	let t = e.kind?.toLowerCase();
	if (t !== "execute" && t !== "bash" && t !== "shell" && t !== "terminal" || !yo(e.rawInput)) return;
	let n = _o(e.rawInput.command, e.rawInput.cmd);
	if (!n?.trim()) return;
	let r = _o(e.rawInput.cwd, e.rawInput.workdir), { text: i, remaining: a } = ro(e.content), o = yo(e.rawOutput) ? e.rawOutput : void 0, s = i ?? _o(o?.output, o?.error) ?? (typeof e.rawOutput == "string" ? e.rawOutput : ""), c = e.status === "pending" || e.status === "in_progress";
	return {
		kind: "terminal",
		command: n,
		...r ? { cwd: r } : {},
		output: s,
		displayOutput: vo(s),
		running: c,
		failed: e.status === "failed" || e.status === "cancelled",
		supplementary: a
	};
}
function $a(e) {
	if (e.kind?.toLowerCase() !== "read" || e.status !== "completed") return;
	let t = yo(e.rawInput) ? e.rawInput : void 0, n = yo(e.rawOutput) ? e.rawOutput : void 0, r = yo(n?.metadata) ? n.metadata : void 0, i = yo(r?.display) ? r.display : void 0;
	if (i?.type === "directory") return;
	let { text: a, remaining: o } = ro(e.content), s = i?.type === "file" && typeof i.text == "string" ? i.text : void 0, c = a ?? s;
	if (c === void 0) return;
	let l = i?.type === "file", u = lo(c), d = uo(u?.text ?? c);
	if (!l && !u && !d) return;
	let f = u?.text ?? c, p = go(t?.offset) ?? 1, m = d ?? fo(f).map((e, t) => ({
		number: p + t,
		text: e
	})), h = _o(u?.path, t?.filePath, t?.file_path, t?.filepath, t?.path, ho(e)), g = mo(e.title) ?? h;
	if (g) return {
		kind: "read",
		label: g,
		lines: m,
		copyText: m.map((e) => e.text).join("\n"),
		supplementary: o
	};
}
function eo(e) {
	let t = [], n = [], r = /* @__PURE__ */ new Set(), i = /* @__PURE__ */ new Set(), a = 0, o = 0;
	if (e.content.forEach((e, s) => {
		if (!yo(e) || e.type !== "diff") return;
		let c = oo(e);
		if (c) {
			r.add(s), i.add(c.path);
			let e = [{
				kind: "meta",
				text: c.path
			}];
			if (c.oldText !== null) for (let t of po(c.oldText)) e.push({
				kind: "delete",
				text: `- ${t}`
			}), o += 1;
			for (let t of po(c.newText)) e.push({
				kind: "add",
				text: `+ ${t}`
			}), a += 1;
			t.push(...e), n.push(e.map((e) => e.text).join("\n"));
			return;
		}
		let l = so(e);
		if (l) {
			r.add(s);
			for (let e of l.paths) i.add(e);
			t.push(...l.rows), n.push(l.copyText), a += l.rows.filter((e) => e.kind === "add").length, o += l.rows.filter((e) => e.kind === "delete").length;
		}
	}), t.length) return {
		kind: "diff",
		rows: t,
		copyText: n.join("\n\n"),
		added: a,
		removed: o,
		files: i.size,
		supplementary: e.content.filter((e, t) => !r.has(t))
	};
}
function to(e) {
	let t = e.rawInput === void 0 ? void 0 : no(Za(e.rawInput));
	if (e.content.length) {
		let n = io(e.content);
		return {
			kind: "io",
			...t ? { input: t } : {},
			output: {
				values: e.content,
				copyText: n
			}
		};
	}
	let n = e.rawOutput === void 0 ? void 0 : no(Za(e.rawOutput));
	return {
		kind: "io",
		...t ? { input: t } : {},
		...n ? { output: n } : {}
	};
}
function no(e) {
	return {
		text: e,
		copyText: e
	};
}
function ro(e) {
	let t = [], n = [];
	for (let r of e) {
		let e = ao(r);
		e === void 0 ? n.push(r) : t.push(e);
	}
	return {
		...t.length ? { text: t.join("\n") } : {},
		remaining: n
	};
}
function io(e) {
	return e.flatMap((e) => {
		let t = ao(e);
		return t === void 0 ? [] : [t];
	}).join("\n");
}
function ao(e) {
	if (!(!yo(e) || e.type !== "content" || !yo(e.content))) return e.content.type === "text" && typeof e.content.text == "string" ? e.content.text : void 0;
}
function oo(e) {
	if (!(typeof e.path != "string" || !e.path.trim() || typeof e.newText != "string") && (e.oldText === void 0 || e.oldText === null || typeof e.oldText == "string")) return {
		path: e.path,
		oldText: typeof e.oldText == "string" ? e.oldText : null,
		newText: e.newText
	};
}
function so(e) {
	if (!Array.isArray(e.changes)) return;
	let t = e.changes.filter(yo);
	if (t.length !== e.changes.length) return;
	let n = [];
	for (let e of t) {
		if (typeof e.operation != "string" || !e.operation.trim() || typeof e.path != "string" || !e.path.trim()) return;
		n.push(e.path), typeof e.oldPath == "string" && n.push(e.oldPath);
	}
	let r = typeof e.patch == "string" ? e.patch : yo(e.patch) && typeof e.patch.text == "string" ? e.patch.text : void 0;
	if (r !== void 0) return {
		rows: r.split(/\r?\n/).map(co),
		copyText: r,
		paths: n
	};
	let i = t.map((e) => {
		let t = typeof e.oldPath == "string" ? e.oldPath : void 0;
		return t ? `${String(e.operation)} ${t} -> ${String(e.path)}` : `${String(e.operation)} ${String(e.path)}`;
	}).join("\n");
	return {
		rows: i.split("\n").filter(Boolean).map((e) => ({
			kind: "meta",
			text: e
		})),
		copyText: i,
		paths: n
	};
}
function co(e) {
	return e.startsWith("+") && !e.startsWith("+++") ? {
		kind: "add",
		text: e
	} : e.startsWith("-") && !e.startsWith("---") ? {
		kind: "delete",
		text: e
	} : e.startsWith(" ") ? {
		kind: "context",
		text: e
	} : {
		kind: "meta",
		text: e
	};
}
function lo(e) {
	let t = /^<path>([^\r\n]*)<\/path>\r?\n<type>file<\/type>\r?\n<content>\r?\n([\s\S]*)\r?\n<\/content>$/.exec(e);
	return t?.[1] !== void 0 && t[2] !== void 0 ? {
		path: t[1],
		text: t[2]
	} : void 0;
}
function uo(e) {
	let t = fo(e);
	if (!t.length) return;
	let n = [], r = 0;
	for (let e of t) {
		let t = /^(\d+):(?: |$)(.*)$/.exec(e), i = t ? Number(t[1]) : NaN;
		if (!t || !Number.isSafeInteger(i) || i <= r) return;
		n.push({
			number: i,
			text: t[2] ?? ""
		}), r = i;
	}
	return n;
}
function fo(e) {
	return e ? (e.endsWith("\n") ? e.slice(0, -1) : e).split(/\r?\n/) : [];
}
function po(e) {
	return e ? fo(e) : [];
}
function mo(e) {
	let t = e.trim(), n = t.toLowerCase();
	return t && n !== "read" && n !== "tool" ? t : void 0;
}
function ho(e) {
	return e.locations.find((e) => typeof e.path == "string")?.path;
}
function go(e) {
	return typeof e == "number" && Number.isSafeInteger(e) && e > 0 ? e : void 0;
}
function _o(...e) {
	return e.find((e) => typeof e == "string");
}
function vo(e) {
	return e.replaceAll(/\u001b\][^\u0007\u001b]*(?:\u0007|\u001b\\)?/g, "").replaceAll(/\u001b\[[\u0030-\u003f]*[\u0020-\u002f]*[\u0040-\u007e]/g, "").replaceAll("\r\n", "\n").replaceAll("\r", "\n").replaceAll(/[\u0000-\u0008\u000b\u000c\u000e-\u001a\u001c-\u001f\u007f]/g, "");
}
function yo(e) {
	return typeof e == "object" && !!e && !Array.isArray(e);
}
//#endregion
//#region src/react/ToolBlocks.tsx
function bo({ tool: e, labels: t, renderContent: n }) {
	let r = Xa(e);
	switch (r.kind) {
		case "terminal": return /* @__PURE__ */ Z(O, { children: [/* @__PURE__ */ Z(xo, {
			model: r,
			status: e.status,
			labels: t
		}), /* @__PURE__ */ Z(Do, {
			values: r.supplementary,
			render: n
		})] });
		case "read": return /* @__PURE__ */ Z(O, { children: [/* @__PURE__ */ Z(So, {
			model: r,
			labels: t
		}), /* @__PURE__ */ Z(Do, {
			values: r.supplementary,
			render: n
		})] });
		case "diff": return /* @__PURE__ */ Z(O, { children: [/* @__PURE__ */ Z(wo, {
			model: r,
			labels: t
		}), /* @__PURE__ */ Z(Do, {
			values: r.supplementary,
			render: n
		})] });
		case "io": return !r.input && !r.output ? /* @__PURE__ */ Z("span", {
			className: "paui-muted",
			children: t.tool
		}) : /* @__PURE__ */ Z("div", {
			className: "paui-tool-block paui-tool-io",
			"data-tool-block": "io",
			children: [
				r.input ? /* @__PURE__ */ Z(Eo, {
					label: t.toolInput,
					section: r.input,
					labels: t,
					render: n
				}) : null,
				r.input && r.output ? /* @__PURE__ */ Z("span", {
					className: "paui-tool-io__divider",
					"aria-hidden": "true"
				}) : null,
				r.output ? /* @__PURE__ */ Z(Eo, {
					label: t.toolOutput,
					section: r.output,
					labels: t,
					render: n,
					failed: e.status === "failed" || e.status === "cancelled"
				}) : null
			]
		});
	}
}
function xo({ model: e, status: t, labels: n }) {
	let r = e.displayOutput.trim().length > 0;
	return /* @__PURE__ */ Z("div", {
		className: "paui-tool-block paui-tool-terminal",
		"data-tool-block": "terminal",
		"data-state": e.failed ? "failed" : e.running ? "running" : "completed",
		children: [/* @__PURE__ */ Z("div", {
			className: "paui-tool-terminal__header",
			children: [/* @__PURE__ */ Z("div", {
				className: "paui-tool-terminal__prompt",
				children: [/* @__PURE__ */ Z("span", {
					className: "paui-sr-only",
					children: t
				}), jo(e.command).map((t, n) => /* @__PURE__ */ Z("div", {
					className: "paui-tool-terminal__prompt-line",
					children: [
						n === 0 ? /* @__PURE__ */ Z("span", {
							className: "paui-tool-terminal__state",
							"aria-hidden": "true"
						}) : null,
						/* @__PURE__ */ Z("span", {
							className: "paui-tool-terminal__cwd",
							children: n === 0 && e.cwd ? e.cwd : "$"
						}),
						/* @__PURE__ */ Z("span", {
							className: "paui-tool-terminal__command",
							children: t
						})
					]
				}, n))]
			}), !e.running && r ? /* @__PURE__ */ Z(Oo, {
				text: e.output,
				labels: n
			}) : null]
		}), e.running ? null : r ? /* @__PURE__ */ Z("pre", {
			className: "paui-tool-terminal__output",
			children: e.displayOutput
		}) : /* @__PURE__ */ Z("div", {
			className: "paui-tool-block__empty",
			children: n.toolNoOutput
		})]
	});
}
function So({ model: e, labels: t }) {
	let [n, r] = F(!1), i = Ao(e.lines, n);
	return /* @__PURE__ */ Z("div", {
		className: "paui-tool-block paui-tool-read",
		"data-tool-block": "read",
		children: [/* @__PURE__ */ Z("div", {
			className: "paui-tool-block__banner",
			children: [/* @__PURE__ */ Z("span", {
				className: "paui-tool-block__label",
				children: e.label
			}), e.copyText ? /* @__PURE__ */ Z(Oo, {
				text: e.copyText,
				labels: t
			}) : null]
		}), /* @__PURE__ */ Z("div", {
			className: "paui-tool-read__body",
			children: [
				/* @__PURE__ */ Z(Co, { lines: i.head }),
				i.hidden > 0 ? /* @__PURE__ */ Z(ko, {
					expanded: n,
					hidden: i.hidden,
					labels: t,
					onClick: () => r((e) => !e)
				}) : null,
				/* @__PURE__ */ Z(Co, { lines: i.tail })
			]
		})]
	});
}
function Co({ lines: e }) {
	return e.map((e) => /* @__PURE__ */ Z("div", {
		className: "paui-tool-read__line",
		children: [/* @__PURE__ */ Z("span", {
			className: "paui-tool-read__gutter",
			"aria-hidden": "true",
			children: e.number
		}), /* @__PURE__ */ Z("span", {
			className: "paui-tool-read__content",
			children: e.text
		})]
	}, e.number));
}
function wo({ model: e, labels: t }) {
	let [n, r] = F(!1), i = Ao(e.rows, n);
	return /* @__PURE__ */ Z("div", {
		className: "paui-tool-block paui-tool-diff",
		"data-tool-block": "diff",
		children: [
			/* @__PURE__ */ Z("div", {
				className: "paui-tool-block__banner paui-tool-diff__banner",
				children: [/* @__PURE__ */ Z("span", {
					className: "paui-tool-block__label",
					children: t.changedFiles
				}), /* @__PURE__ */ Z(Oo, {
					text: e.copyText,
					labels: t
				})]
			}),
			/* @__PURE__ */ Z("div", {
				className: "paui-tool-diff__body",
				children: [
					/* @__PURE__ */ Z(To, { rows: i.head }),
					i.hidden > 0 ? /* @__PURE__ */ Z(ko, {
						expanded: n,
						hidden: i.hidden,
						labels: t,
						onClick: () => r((e) => !e)
					}) : null,
					/* @__PURE__ */ Z(To, { rows: i.tail })
				]
			}),
			/* @__PURE__ */ Z("div", {
				className: "paui-tool-diff__footer",
				children: [
					"+",
					e.added,
					" −",
					e.removed,
					" · ",
					e.files,
					" ",
					t.changedFiles
				]
			})
		]
	});
}
function To({ rows: e }) {
	return e.map((e, t) => /* @__PURE__ */ Z("div", {
		className: "paui-tool-diff__line",
		"data-line-kind": e.kind,
		children: e.text
	}, t));
}
function Eo({ label: e, section: t, labels: n, render: r, failed: i = !1 }) {
	return /* @__PURE__ */ Z("section", {
		className: "paui-tool-io__section",
		"data-error": i || void 0,
		children: [/* @__PURE__ */ Z("div", {
			className: "paui-tool-io__section-header",
			children: [/* @__PURE__ */ Z("strong", { children: e }), t.copyText ? /* @__PURE__ */ Z(Oo, {
				text: t.copyText,
				labels: n
			}) : null]
		}), /* @__PURE__ */ Z("div", {
			className: "paui-tool-io__content",
			children: [t.text === void 0 ? null : /* @__PURE__ */ Z("pre", { children: t.text }), t.values?.map(r)]
		})]
	});
}
function Do({ values: e, render: t }) {
	return e.length ? /* @__PURE__ */ Z("div", {
		className: "paui-tool-supplementary",
		children: e.map(t)
	}) : null;
}
function Oo({ text: e, labels: t }) {
	let { copied: n, copy: r } = ka(e), i = n ? t.copied : t.copy;
	return /* @__PURE__ */ Z("button", {
		className: "paui-tool-block__copy",
		type: "button",
		"aria-label": i,
		title: i,
		onClick: (e) => r(e.currentTarget),
		children: i
	});
}
function ko({ expanded: e, hidden: t, labels: n, onClick: r }) {
	return /* @__PURE__ */ Z("button", {
		className: "paui-tool-block__fold",
		type: "button",
		"aria-expanded": e,
		onClick: r,
		children: e ? n.toolCollapseLines : n.toolExpandLines(t)
	});
}
function Ao(e, t) {
	let n = Math.max(0, e.length - 8);
	return n ? t ? {
		head: e,
		tail: [],
		hidden: n
	} : {
		head: e.slice(0, 4),
		tail: e.slice(-4),
		hidden: n
	} : {
		head: e,
		tail: [],
		hidden: 0
	};
}
function jo(e) {
	return (e.endsWith("\n") ? e.slice(0, -1) : e).split("\n");
}
//#endregion
//#region src/react/Chat.tsx
var Mo = Ve(void 0), No = /* @__PURE__ */ new WeakMap(), Po = 0, Fo = {
	phase: "connecting",
	loadedSessions: [],
	sessionTrail: [],
	historyGap: !1,
	activities: [],
	configOptions: [],
	commands: [],
	contextSelection: {
		items: [],
		canAdd: !1,
		canRemove: !1,
		busy: !1
	},
	interactions: [],
	authMethods: [],
	capabilities: {
		listSessions: !1,
		loadSession: !1,
		resumeSession: !1,
		closeSession: !1,
		deleteSession: !1
	}
}, Io = {
	ready: new Promise(() => void 0),
	getSnapshot: () => Fo,
	subscribe: () => () => void 0,
	appendNotice: () => !1,
	send() {
		throw Error("The chat session is still connecting");
	},
	async cancel() {},
	async addContext() {},
	async removeContext() {},
	async reconnect() {},
	async newSession() {},
	async listSessions() {
		return { sessions: [] };
	},
	async openSession() {},
	async openChildSession() {},
	async openAncestorSession() {},
	async closeSession() {},
	async deleteSession() {},
	async setConfigOption() {},
	async authenticate() {},
	async logout() {},
	respondPermission: () => !1,
	respondElicitation: () => !1,
	async destroy() {}
};
function Q(e) {
	let t = rt(Mo);
	if (!t) throw Error(`pretty-aui: ${e} must be rendered inside a ChatRoot.`);
	return t;
}
function Lo(e) {
	return /* @__PURE__ */ Z(Ro, {
		...e,
		children: [
			/* @__PURE__ */ Z(Vo, {}),
			/* @__PURE__ */ Z(Ho, {}),
			/* @__PURE__ */ Z(Uo, {}),
			/* @__PURE__ */ Z(vs, {})
		]
	});
}
function Ro(e) {
	if ("controller" in e) {
		let { controller: t, ...n } = e;
		return /* @__PURE__ */ Z(Bo, {
			...n,
			controller: t
		}, Is(t));
	}
	let { options: t, ...n } = e;
	return /* @__PURE__ */ Z(zo, {
		...n,
		options: t
	});
}
function zo(e) {
	let { options: t, ...n } = e, r = L(t), [i, a] = F();
	return I(() => {
		let e = cn(r.current);
		return a(e), () => {
			e.destroy();
		};
	}, []), i ? /* @__PURE__ */ Z(Bo, {
		...n,
		controller: i
	}, Is(i)) : /* @__PURE__ */ Z(Bo, {
		...n,
		controller: Io
	}, "connecting");
}
function Bo(e) {
	let { controller: t } = e, n = pt(nt((e) => Rs(t, e), [t]), nt(() => t.getSnapshot(), [t]), nt(() => t.getSnapshot(), [t])), r = tt(() => ({
		...Ta,
		...e.labels
	}), [e.labels]), i = it().replaceAll(":", ""), [a, o] = F(), s = nt((e) => {
		o(void 0), e().catch((e) => {
			o(e instanceof Error ? e.message : String(e));
		});
	}, []), c = e.colorScheme ?? "system", l = e.surface ?? "inline", u = tt(() => ({
		controller: t,
		snapshot: n,
		labels: r,
		toolActivityRenderer: e.toolActivityRenderer,
		actionError: a,
		runAction: s,
		ids: {
			instance: `paui-${i}`,
			sessionsTitle: `paui-${i}-sessions-title`
		}
	}), [
		a,
		t,
		i,
		r,
		e.toolActivityRenderer,
		s,
		n
	]);
	return /* @__PURE__ */ Z("section", {
		className: ["pretty-aui", e.className].filter(Boolean).join(" "),
		"data-pretty-aui-slot": "root",
		"data-surface": l,
		"data-scheme": c,
		"data-phase": n.phase,
		style: e.style,
		"aria-label": n.agentName ?? r.assistantName,
		children: /* @__PURE__ */ Z(Mo.Provider, {
			value: u,
			children: e.children
		})
	});
}
function Vo() {
	let { controller: e, snapshot: t, labels: n, runAction: r } = Q("ChatHeader"), [i, a] = F(!1), o = t.sessionTitle ?? n.sessionUntitled, s = t.sessionTrail.at(-1), c = t.protocolVersion !== void 0 && t.phase !== "connecting" && t.phase !== "auth_required" && t.phase !== "closed" && t.loadedSessions.length < 16;
	return /* @__PURE__ */ Z(O, { children: [/* @__PURE__ */ Z("header", {
		className: "paui-header",
		"data-pretty-aui-slot": "header",
		children: [/* @__PURE__ */ Z("div", {
			className: `paui-identity${s ? " paui-identity--child" : ""}`,
			children: [/* @__PURE__ */ Z("span", {
				className: "paui-presence",
				"data-phase": t.phase,
				"aria-hidden": "true"
			}), s ? /* @__PURE__ */ Z("div", {
				className: "paui-lineage",
				"data-depth": t.sessionTrail.length,
				children: [
					/* @__PURE__ */ Z("button", {
						className: "paui-lineage__back",
						type: "button",
						disabled: t.phase !== "idle",
						"aria-label": n.backToSession(s.title ?? s.sessionId),
						onClick: () => r(() => e.openAncestorSession(s.sessionId)),
						children: /* @__PURE__ */ Z(Qs, {})
					}),
					/* @__PURE__ */ Z("div", {
						className: "paui-lineage__titles",
						children: [t.sessionTrail.map((n) => {
							let i = n.title ?? n.sessionId;
							return /* @__PURE__ */ Z("span", {
								className: "paui-lineage__ancestor",
								children: [/* @__PURE__ */ Z("button", {
									type: "button",
									disabled: t.phase !== "idle",
									onClick: () => r(() => e.openAncestorSession(n.sessionId)),
									children: i
								}), /* @__PURE__ */ Z("span", {
									"aria-hidden": "true",
									children: "/"
								})]
							}, n.sessionId);
						}), /* @__PURE__ */ Z("strong", { children: o })]
					}),
					/* @__PURE__ */ Z("span", {
						className: "paui-protocol",
						children: t.protocolVersion ? `ACP v${t.protocolVersion}` : t.phase
					})
				]
			}) : /* @__PURE__ */ Z("div", { children: [/* @__PURE__ */ Z("strong", { children: o }), /* @__PURE__ */ Z("span", {
				className: "paui-protocol",
				children: t.protocolVersion ? `ACP v${t.protocolVersion}` : t.phase
			})] })]
		}), /* @__PURE__ */ Z("div", {
			className: "paui-header__actions",
			children: [
				t.usage ? /* @__PURE__ */ Z("span", {
					className: "paui-usage",
					children: n.usage(t.usage.used, t.usage.size)
				}) : null,
				t.capabilities.listSessions || t.loadedSessions.length > 1 ? /* @__PURE__ */ Z("button", {
					className: "paui-icon-button",
					type: "button",
					onClick: () => a(!0),
					children: [/* @__PURE__ */ Z(Ws, {}), /* @__PURE__ */ Z("span", {
						className: "paui-sr-only",
						children: n.sessions
					})]
				}) : null,
				/* @__PURE__ */ Z("button", {
					className: "paui-icon-button",
					type: "button",
					disabled: !c,
					onClick: () => r(() => e.newSession()),
					children: [/* @__PURE__ */ Z(Gs, {}), /* @__PURE__ */ Z("span", {
						className: "paui-sr-only",
						children: n.newChat
					})]
				})
			]
		})]
	}), i ? /* @__PURE__ */ Z(Es, {
		controller: e,
		snapshot: t,
		labels: n,
		onClose: () => a(!1)
	}) : null] });
}
function Ho() {
	let { snapshot: e, labels: t, toolActivityRenderer: n } = Q("ChatTranscript"), r = L(null), i = L(null), a = L(!0), o = L(0), s = Ls(e), c = L(s), l = L(/* @__PURE__ */ new Map()), [u, d] = F(!0), f = nt((e = "auto") => {
		let t = r.current;
		t && (typeof t.scrollTo == "function" ? t.scrollTo({
			top: t.scrollHeight,
			behavior: e
		}) : t.scrollTop = t.scrollHeight, o.current = t.scrollTop, a.current = !0, d(!0));
	}, []), p = nt(() => {
		let e = r.current;
		if (!e) return;
		let t = e.scrollHeight - e.scrollTop - e.clientHeight, n = e.scrollTop < o.current - 1, i = t <= 24 || !n && a.current;
		o.current = e.scrollTop, a.current = i, l.current.set(s, {
			top: e.scrollTop,
			pinned: i
		}), d(i);
	}, [s]);
	et(() => {
		let e = c.current;
		if (e === s) return;
		let t = r.current;
		if (!t) return;
		l.current.set(e, {
			top: t.scrollTop,
			pinned: a.current
		}), c.current = s;
		let n = l.current.get(s);
		n ? (t.scrollTop = n.top, o.current = n.top, a.current = n.pinned, d(n.pinned)) : f();
	}, [f, s]), et(() => {
		a.current && f();
	}, [
		f,
		e.activities,
		e.historyGap
	]), I(() => {
		let e = i.current;
		if (!e || typeof ResizeObserver > "u") return;
		let t = new ResizeObserver(() => {
			a.current && f();
		});
		return t.observe(e), r.current && t.observe(r.current), () => t.disconnect();
	}, [f]);
	let m = tt(() => Go(e.activities), [e.activities]), h = e.phase === "running" || e.phase === "awaiting_user" || e.phase === "cancelling", g = h ? Wo(m) : -1, _ = tt(() => as(e.activities, h), [e.activities, h]);
	return /* @__PURE__ */ Z(O, { children: [/* @__PURE__ */ Z("main", {
		ref: r,
		className: "paui-body",
		"data-pretty-aui-slot": "transcript",
		tabIndex: 0,
		onScroll: p,
		children: /* @__PURE__ */ Z("div", {
			className: "paui-transcript",
			ref: i,
			children: [
				e.historyGap ? /* @__PURE__ */ Z("aside", {
					className: "paui-notice",
					role: "status",
					children: [/* @__PURE__ */ Z(mc, {}), /* @__PURE__ */ Z("div", { children: [/* @__PURE__ */ Z("strong", { children: t.historyGapTitle }), /* @__PURE__ */ Z("span", { children: t.historyGap })] })]
				}) : null,
				e.activities.length ? null : /* @__PURE__ */ Z("div", {
					className: "paui-empty",
					children: [
						/* @__PURE__ */ Z(gc, {}),
						/* @__PURE__ */ Z("strong", { children: t.emptyTitle }),
						/* @__PURE__ */ Z("p", { children: t.emptyDescription })
					]
				}),
				m.map((e, r) => e.kind === "notice" ? /* @__PURE__ */ Z(Ko, {
					group: e,
					labels: t
				}, e.id) : /* @__PURE__ */ Z(qo, {
					group: e,
					labels: t,
					toolActivityRenderer: n,
					active: r === g,
					completedAnswerIds: _
				}, e.id))
			]
		})
	}), u ? null : /* @__PURE__ */ Z("div", {
		className: "paui-to-bottom-row",
		children: /* @__PURE__ */ Z("button", {
			className: "paui-to-bottom",
			type: "button",
			onClick: () => f("smooth"),
			"aria-label": t.scrollToLatest,
			children: /* @__PURE__ */ Z(Zs, {})
		})
	})] });
}
function Uo() {
	let { controller: e, snapshot: t, labels: n, actionError: r, runAction: i } = Q("ChatInteractions"), a = L(null);
	return I(() => {
		if (!t.interactions.length) return;
		let e = a.current;
		if (!e) return;
		let n = Os(e);
		n && e.contains(n) || e.querySelector(As)?.focus();
	}, [t.interactions.map((e) => e.id).join("\0"), t.interactions.length]), /* @__PURE__ */ Z("div", {
		ref: a,
		className: "paui-interactions",
		"data-pretty-aui-slot": "interactions",
		children: [
			t.phase === "auth_required" ? /* @__PURE__ */ Z(Ts, {}) : null,
			t.interactions.map((t) => t.type === "permission" ? /* @__PURE__ */ Z(xs, {
				interaction: t,
				controller: e,
				labels: n
			}, t.id) : /* @__PURE__ */ Z(Ss, {
				interaction: t,
				controller: e,
				labels: n
			}, t.id)),
			t.error ? /* @__PURE__ */ Z("aside", {
				className: "paui-error",
				role: "alert",
				children: [/* @__PURE__ */ Z("div", { children: [/* @__PURE__ */ Z("strong", { children: n.error }), /* @__PURE__ */ Z("span", { children: t.error.message })] }), t.error.retryable ? /* @__PURE__ */ Z("button", {
					type: "button",
					onClick: () => i(() => e.reconnect()),
					children: n.retry
				}) : null]
			}) : null,
			r && !t.error ? /* @__PURE__ */ Z("aside", {
				className: "paui-error",
				role: "alert",
				children: /* @__PURE__ */ Z("div", { children: [/* @__PURE__ */ Z("strong", { children: n.error }), /* @__PURE__ */ Z("span", { children: r })] })
			}) : null
		]
	});
}
function Wo(e) {
	for (let t = e.length - 1; t >= 0; --t) if (e[t]?.kind === "turn") return t;
	return -1;
}
function Go(e) {
	let t = [], n, r = () => {
		n &&= (t.push({
			kind: "turn",
			...n
		}), void 0);
	};
	for (let i of e) {
		if (i.type === "notice") {
			r();
			let e = t.at(-1);
			e?.kind === "notice" ? t[t.length - 1] = {
				...e,
				activities: [...e.activities, i]
			} : t.push({
				kind: "notice",
				id: i.id,
				activities: [i]
			});
			continue;
		}
		i.type === "message" && i.role === "user" ? (r(), n = {
			id: i.id,
			user: i,
			activities: []
		}) : (n ??= {
			id: i.id,
			activities: []
		}, n.activities.push(i));
	}
	return r(), t;
}
function Ko({ group: e, labels: t }) {
	return /* @__PURE__ */ Z("div", {
		className: "paui-notice-group",
		children: e.activities.map((e) => /* @__PURE__ */ Z(Jo, {
			activity: e,
			labels: t,
			running: !1,
			showMessageActions: !1
		}, e.id))
	});
}
function qo({ group: e, labels: t, toolActivityRenderer: n, active: r, completedAnswerIds: i }) {
	return /* @__PURE__ */ Z("article", {
		className: "paui-turn",
		children: [e.user ? /* @__PURE__ */ Z(is, {
			message: e.user,
			labels: t,
			showActions: !0
		}) : null, e.activities.length ? /* @__PURE__ */ Z("div", {
			className: "paui-activities",
			children: e.activities.map((a, o) => /* @__PURE__ */ Z(Jo, {
				activity: a,
				labels: t,
				toolActivityRenderer: n,
				running: r && o === e.activities.length - 1,
				showMessageActions: i.has(a.id)
			}, a.id))
		}) : null]
	});
}
var Jo = gt(function({ activity: e, labels: t, toolActivityRenderer: n, running: r, showMessageActions: i }) {
	return /* @__PURE__ */ Z("div", {
		className: "paui-activity",
		"data-pretty-aui-slot": "activity",
		"data-kind": e.type === "message" ? e.role : e.type === "tool" && e.subagent ? "subagent" : e.type,
		"data-level": e.type === "notice" ? e.level : void 0,
		"data-status": Bs(e),
		children: /* @__PURE__ */ Z(Yo, {
			activity: e,
			labels: t,
			toolActivityRenderer: n,
			running: r,
			showMessageActions: i
		})
	});
});
function Yo({ activity: e, labels: t, toolActivityRenderer: n, running: r, showMessageActions: i }) {
	switch (e.type) {
		case "message": return /* @__PURE__ */ Z(is, {
			message: e,
			labels: t,
			running: r,
			showActions: i
		});
		case "context": return /* @__PURE__ */ Z(Xo, {
			activity: e,
			labels: t
		});
		case "notice": return /* @__PURE__ */ Z("div", {
			className: "paui-host-notice",
			role: e.level === "error" ? "alert" : "status",
			children: [/* @__PURE__ */ Z("span", {
				className: "paui-host-notice__icon",
				"aria-hidden": "true",
				children: e.level === "error" ? /* @__PURE__ */ Z(hc, {}) : /* @__PURE__ */ Z(mc, {})
			}), /* @__PURE__ */ Z("span", { children: e.text })]
		});
		case "tool": return e.subagent ? /* @__PURE__ */ Z(es, {
			tool: e,
			labels: t,
			renderer: n
		}) : /* @__PURE__ */ Z("details", {
			className: "paui-disclosure paui-tool",
			"data-state": e.status,
			children: [/* @__PURE__ */ Z("summary", {
				className: "paui-flow-summary",
				children: [
					/* @__PURE__ */ Z(ss, { icon: /* @__PURE__ */ Z(ds, { kind: e.kind }) }),
					/* @__PURE__ */ Z("span", {
						className: "paui-flow-title",
						children: us(e.kind, t.tool)
					}),
					/* @__PURE__ */ Z("span", {
						className: "paui-flow-separator",
						"aria-hidden": "true"
					}),
					/* @__PURE__ */ Z("span", {
						className: "paui-flow-preview",
						children: e.title
					}),
					/* @__PURE__ */ Z("span", {
						className: "paui-sr-only",
						children: e.status
					})
				]
			}), /* @__PURE__ */ Z("div", {
				className: "paui-disclosure__body",
				children: /* @__PURE__ */ Z(fs, {
					tool: e,
					labels: t,
					renderer: n
				})
			})]
		});
		case "plan": return /* @__PURE__ */ Z("details", {
			className: "paui-disclosure paui-plan",
			open: !0,
			children: [/* @__PURE__ */ Z("summary", { children: [
				/* @__PURE__ */ Z(ic, {}),
				/* @__PURE__ */ Z("span", { children: t.plan }),
				/* @__PURE__ */ Z(Us, { status: zs(e.entries) })
			] }), /* @__PURE__ */ Z("ol", {
				className: "paui-plan__list",
				children: e.entries.map((e, t) => /* @__PURE__ */ Z("li", {
					"data-status": e.status,
					children: [/* @__PURE__ */ Z("span", {
						className: "paui-plan__mark",
						"aria-hidden": "true"
					}), /* @__PURE__ */ Z("span", { children: e.content })]
				}, `${e.content}-${t}`))
			})]
		});
		case "terminal": return /* @__PURE__ */ Z("details", {
			className: "paui-disclosure paui-terminal",
			children: [/* @__PURE__ */ Z("summary", { children: [
				/* @__PURE__ */ Z(cc, {}),
				/* @__PURE__ */ Z("span", { children: e.title }),
				/* @__PURE__ */ Z(Us, { status: e.exited ? "completed" : "in_progress" })
			] }), /* @__PURE__ */ Z("pre", { children: e.output })]
		});
		case "unsupported": return /* @__PURE__ */ Z("div", {
			className: "paui-unsupported",
			children: t.unsupportedContent(e.kind)
		});
	}
}
function Xo({ activity: e, labels: t }) {
	return /* @__PURE__ */ Z("details", {
		className: "paui-disclosure paui-context-injection",
		children: [/* @__PURE__ */ Z("summary", {
			className: "paui-flow-summary",
			children: [
				/* @__PURE__ */ Z(ss, { icon: /* @__PURE__ */ Z(pc, {}) }),
				/* @__PURE__ */ Z("span", {
					className: "paui-flow-title",
					children: t.contextInjection
				}),
				/* @__PURE__ */ Z("span", {
					className: "paui-flow-separator",
					"aria-hidden": "true"
				}),
				/* @__PURE__ */ Z("span", {
					className: "paui-flow-preview",
					children: e.label
				})
			]
		}), /* @__PURE__ */ Z("div", {
			className: "paui-context-injection__body",
			tabIndex: 0,
			children: e.content.map((n, r) => /* @__PURE__ */ Z(Zo, {
				block: n,
				labels: t
			}, `${e.id}:${r}`))
		})]
	});
}
function Zo({ block: e, labels: t }) {
	if (e.type === "text" && typeof e.text == "string") return /* @__PURE__ */ Z(Qo, {
		text: e.text,
		labels: t
	});
	if (e.type === "resource" && Hs(e.resource)) {
		let n = e.resource;
		return /* @__PURE__ */ Z("section", {
			className: "paui-context-block",
			children: [/* @__PURE__ */ Z("div", {
				className: "paui-context-meta",
				children: [/* @__PURE__ */ Z("span", { children: String(n.uri ?? t.resource) }), typeof n.mimeType == "string" ? /* @__PURE__ */ Z("span", { children: n.mimeType }) : null]
			}), typeof n.text == "string" ? /* @__PURE__ */ Z(Qo, {
				text: n.text,
				labels: t
			}) : typeof n.blob == "string" ? /* @__PURE__ */ Z("span", {
				className: "paui-muted",
				children: `Binary resource · ${n.blob.length.toLocaleString()} base64 characters`
			}) : null]
		});
	}
	if (e.type === "resource_link" && typeof e.uri == "string") {
		let n = typeof e.title == "string" ? e.title : typeof e.name == "string" ? e.name : t.resource, r = typeof e.mimeType == "string" ? e.mimeType : void 0, i = typeof e.description == "string" ? e.description : void 0;
		return /* @__PURE__ */ Z("section", {
			className: "paui-context-block",
			children: [
				/* @__PURE__ */ Z("div", {
					className: "paui-context-meta",
					children: [/* @__PURE__ */ Z("span", { children: n }), r ? /* @__PURE__ */ Z("span", { children: r }) : null]
				}),
				/* @__PURE__ */ Z("span", {
					className: "paui-context-identifier",
					children: e.uri
				}),
				i ? /* @__PURE__ */ Z("span", { children: i }) : null
			]
		});
	}
	return (e.type === "image" || e.type === "audio") && typeof e.mimeType == "string" && typeof e.data == "string" ? /* @__PURE__ */ Z("span", {
		className: "paui-context-meta",
		children: `${us(e.type, e.type)} · ${e.mimeType} · ${e.data.length.toLocaleString()} base64 characters`
	}) : /* @__PURE__ */ Z(Qo, {
		text: Za(e),
		labels: t
	});
}
function Qo({ text: e, labels: t }) {
	let n = $o(e);
	return /* @__PURE__ */ Z(O, { children: [/* @__PURE__ */ Z("pre", {
		className: "paui-context-text",
		children: n.text
	}), n.truncated ? /* @__PURE__ */ Z("span", {
		className: "paui-context-truncated",
		children: t.contextTruncated(e.length)
	}) : null] });
}
function $o(e) {
	if (e.length <= 2e4) return {
		text: e,
		truncated: !1
	};
	let t = 2e4, n = e.charCodeAt(t - 1);
	return n >= 55296 && n <= 56319 && --t, {
		text: e.slice(0, t),
		truncated: !0
	};
}
function es({ tool: e, labels: t, renderer: n }) {
	let { controller: r, snapshot: i, runAction: a } = Q("ChatTranscript"), o = e.subagent, s = e.status === "pending" || e.status === "in_progress", c = ts(e.id, s), l = rs(e, t), u = i.capabilities.loadSession || i.capabilities.resumeSession;
	return /* @__PURE__ */ Z("div", {
		className: "paui-subagent-row",
		children: [/* @__PURE__ */ Z("details", {
			className: "paui-disclosure paui-subagent",
			"data-state": e.status,
			"data-running": s || void 0,
			children: [/* @__PURE__ */ Z("summary", {
				className: "paui-flow-summary",
				children: [
					/* @__PURE__ */ Z(ss, { icon: /* @__PURE__ */ Z(nc, {}) }),
					/* @__PURE__ */ Z("span", {
						className: "paui-flow-title",
						children: t.agentName(o.agent)
					}),
					o.description ? /* @__PURE__ */ Z(O, { children: [/* @__PURE__ */ Z("span", {
						className: "paui-flow-separator",
						"aria-hidden": "true"
					}), /* @__PURE__ */ Z("span", {
						className: "paui-flow-preview",
						children: o.description
					})] }) : null,
					/* @__PURE__ */ Z("span", {
						className: "paui-subagent-status",
						"data-status": e.status,
						children: [s ? /* @__PURE__ */ Z("span", {
							className: "paui-subagent-status__ongoing",
							children: [/* @__PURE__ */ Z("span", {
								className: "paui-subagent-status__spinner",
								"aria-hidden": "true"
							}), /* @__PURE__ */ Z("span", { children: t.agentOngoing })]
						}) : /* @__PURE__ */ Z("span", { children: l }), c ? /* @__PURE__ */ Z("span", { children: t.agentObserved(c) }) : null]
					})
				]
			}), /* @__PURE__ */ Z("div", {
				className: "paui-disclosure__body",
				children: /* @__PURE__ */ Z(fs, {
					tool: e,
					labels: t,
					renderer: n
				})
			})]
		}), o.sessionId ? /* @__PURE__ */ Z("button", {
			className: "paui-subagent-open",
			type: "button",
			disabled: !u || i.phase !== "idle",
			"aria-label": t.openChildSession,
			onClick: () => a(() => r.openChildSession(o.sessionId)),
			children: /* @__PURE__ */ Z(rc, {})
		}) : null]
	});
}
function ts(e, t) {
	let n = L(Date.now()), [r, i] = F(n.current);
	return I(() => {
		n.current = Date.now(), i(n.current);
	}, [e]), I(() => {
		if (!t) return;
		let e = window.setInterval(() => i(Date.now()), 1e3);
		return () => window.clearInterval(e);
	}, [t]), t ? ns(r - n.current) : void 0;
}
function ns(e) {
	let t = Math.max(0, Math.floor(e / 1e3));
	if (t < 60) return `${t}s`;
	let n = Math.floor(t / 60), r = t % 60;
	return n < 60 ? `${n}m ${String(r).padStart(2, "0")}s` : `${Math.floor(n / 60)}h ${String(n % 60).padStart(2, "0")}m`;
}
function rs(e, t) {
	return e.subagent?.background && e.status === "completed" ? t.agentBackground : e.status === "completed" ? t.agentCompleted : e.status === "failed" ? t.agentFailed : e.status === "cancelled" ? t.agentCancelled : us(e.status, t.agentCompleted);
}
function is({ message: e, labels: t, running: n = !1, showActions: r = !1 }) {
	return e.role === "thought" ? /* @__PURE__ */ Z(os, {
		message: e,
		labels: t,
		running: n
	}) : /* @__PURE__ */ Z("div", {
		className: "paui-message",
		"data-pretty-aui-slot": "message",
		"data-role": e.role,
		"data-pending": e.pending || void 0,
		"data-time-hover-root": r || void 0,
		"aria-live": e.role === "assistant" && n ? "polite" : void 0,
		"aria-atomic": e.role === "assistant" && n ? "false" : void 0,
		children: [/* @__PURE__ */ Z("div", {
			className: "paui-message__bubble",
			children: [/* @__PURE__ */ Z("span", {
				className: "paui-message__label",
				children: e.role === "user" ? t.you : t.assistantName
			}), /* @__PURE__ */ Z("div", {
				className: "paui-message__content",
				children: e.content.map((e, n) => /* @__PURE__ */ Z(gs, {
					block: e,
					labels: t
				}, n))
			})]
		}), r ? /* @__PURE__ */ Z(Pa, {
			content: e.content,
			timestamp: e.timestamp,
			clock: e.role === "user" ? "start" : "end",
			labels: t
		}) : null]
	});
}
function as(e, t) {
	let n = /* @__PURE__ */ new Set(), r = !1, i, a = () => {
		i && n.add(i), r = !1, i = void 0;
	};
	for (let t of e) if (t.type !== "notice") {
		if (t.type === "message" && t.role === "user") {
			r && a(), r = !0;
			continue;
		}
		r = !0, t.type === "message" && t.role === "assistant" && (i = t.id);
	}
	return !t && r && a(), n;
}
function os({ message: e, labels: t, running: n }) {
	let r = L(null), i = cs(e.content, n);
	return et(() => {
		let e = r.current;
		e && (e.scrollLeft = n ? e.scrollWidth - e.clientWidth : 0);
	}, [i, n]), /* @__PURE__ */ Z("details", {
		className: "paui-thought",
		"data-running": n || void 0,
		children: [/* @__PURE__ */ Z("summary", {
			className: "paui-flow-summary",
			children: [
				/* @__PURE__ */ Z(ss, { icon: /* @__PURE__ */ Z(ac, {}) }),
				/* @__PURE__ */ Z("span", {
					className: "paui-flow-title",
					children: t.thinking
				}),
				i ? /* @__PURE__ */ Z(O, { children: [/* @__PURE__ */ Z("span", {
					className: "paui-flow-separator",
					"aria-hidden": "true"
				}), /* @__PURE__ */ Z("span", {
					ref: r,
					className: "paui-flow-preview",
					"data-follow-end": n || void 0,
					children: i
				})] }) : null
			]
		}), /* @__PURE__ */ Z("div", {
			className: "paui-thought__body",
			children: e.content.map((e, n) => /* @__PURE__ */ Z(gs, {
				block: e,
				labels: t
			}, n))
		})]
	});
}
function ss({ icon: e }) {
	return /* @__PURE__ */ Z("span", {
		className: "paui-flow-leading",
		"aria-hidden": "true",
		children: [/* @__PURE__ */ Z("span", {
			className: "paui-flow-icon",
			children: e
		}), /* @__PURE__ */ Z("span", {
			className: "paui-flow-chevron",
			children: /* @__PURE__ */ Z($s, {})
		})]
	});
}
function cs(e, t) {
	if (t) {
		for (let t = e.length - 1; t >= 0; --t) {
			let n = ls(e[t]).trimEnd();
			if (n) return n.slice(n.lastIndexOf("\n") + 1).replace(/\r$/, "").trim();
		}
		return "";
	}
	let n = e.map(ls).filter(Boolean).join("\n").trimEnd();
	return n ? n.split(/\r?\n/)[0]?.trim() ?? "" : "";
}
function ls(e) {
	return e.type === "text" && typeof e.text == "string" ? e.text : e.type === "resource" && Hs(e.resource) && typeof e.resource.text == "string" ? e.resource.text : "";
}
function us(e, t) {
	if (!e) return t;
	let n = e.replaceAll(/[_-]+/g, " ").trim();
	return n ? `${n[0].toUpperCase()}${n.slice(1)}` : t;
}
function ds({ kind: e }) {
	let t = e?.toLowerCase() ?? "";
	return t.includes("read") || t.includes("browse") || t.includes("context") ? /* @__PURE__ */ Z(oc, {}) : t.includes("search") || t.includes("find") ? /* @__PURE__ */ Z(sc, {}) : t.includes("bash") || t.includes("shell") || t.includes("terminal") || t.includes("execute") ? /* @__PURE__ */ Z(cc, {}) : /* @__PURE__ */ Z(tc, {});
}
function fs({ tool: e, labels: t, renderer: n }) {
	let r = /* @__PURE__ */ Z(ps, {
		tool: e,
		labels: t
	});
	return n ? /* @__PURE__ */ Z(hs, {
		fallback: r,
		resetKey: e.id,
		children: /* @__PURE__ */ Z(ms, {
			tool: e,
			renderer: n,
			fallback: r
		})
	}, e.id) : r;
}
function ps({ tool: e, labels: t }) {
	return /* @__PURE__ */ Z(bo, {
		tool: e,
		labels: t,
		renderContent: (e, n) => /* @__PURE__ */ Z(_s, {
			value: e,
			labels: t
		}, n)
	});
}
function ms({ tool: e, renderer: t, fallback: n }) {
	let r = t(e);
	return r === void 0 ? n : r;
}
var hs = class extends k {
	state = { failed: !1 };
	static getDerivedStateFromError() {
		return { failed: !0 };
	}
	componentDidCatch(e) {
		console.error("pretty-aui: custom tool renderer failed", e);
	}
	componentDidUpdate(e) {
		this.state.failed && e.resetKey !== this.props.resetKey && this.setState({ failed: !1 });
	}
	render() {
		return this.state.failed ? this.props.fallback : this.props.children;
	}
};
function gs({ block: e, labels: t }) {
	let n = tt(() => e.type === "text" && typeof e.text == "string" ? Ms(e.text) : void 0, [e]);
	if (n !== void 0) return /* @__PURE__ */ Z("div", {
		className: "paui-markdown",
		dangerouslySetInnerHTML: { __html: n }
	});
	if (e.type === "image" && typeof e.data == "string" && typeof e.mimeType == "string" && e.mimeType.startsWith("image/")) return /* @__PURE__ */ Z("img", {
		className: "paui-media",
		src: `data:${e.mimeType};base64,${e.data}`,
		alt: ""
	});
	if (e.type === "audio" && typeof e.data == "string" && typeof e.mimeType == "string" && e.mimeType.startsWith("audio/")) return /* @__PURE__ */ Z("audio", {
		className: "paui-media",
		controls: !0,
		src: `data:${e.mimeType};base64,${e.data}`
	});
	if (e.type === "resource_link" && typeof e.uri == "string") {
		let n = typeof e.title == "string" ? e.title : typeof e.name == "string" ? e.name : e.uri;
		return Fs(e.uri) ? /* @__PURE__ */ Z("a", {
			className: "paui-resource",
			href: e.uri,
			target: "_blank",
			rel: "noreferrer",
			children: [/* @__PURE__ */ Z(uc, {}), /* @__PURE__ */ Z("span", { children: n })]
		}) : /* @__PURE__ */ Z("span", {
			className: "paui-unsupported",
			children: t.unsupportedContent(t.unsafeResourceLink)
		});
	}
	if (e.type === "resource" && Hs(e.resource)) {
		let n = e.resource, r = typeof n.uri == "string" ? n.uri : t.resource;
		return typeof n.text == "string" ? /* @__PURE__ */ Z("details", {
			className: "paui-resource",
			children: [/* @__PURE__ */ Z("summary", { children: [/* @__PURE__ */ Z(dc, {}), r] }), /* @__PURE__ */ Z("pre", { children: n.text })]
		}) : /* @__PURE__ */ Z("span", {
			className: "paui-resource",
			children: [/* @__PURE__ */ Z(dc, {}), r]
		});
	}
	return /* @__PURE__ */ Z("span", {
		className: "paui-unsupported",
		children: t.unsupportedContent(e.type)
	});
}
function _s({ value: e, labels: t }) {
	if (!Hs(e)) return null;
	if (e.type === "content" && Hs(e.content) && typeof e.content.type == "string") return /* @__PURE__ */ Z(gs, {
		block: e.content,
		labels: t
	});
	if (e.type === "diff") {
		let n = typeof e.path == "string" ? e.path : t.changedFiles, r = typeof e.patch == "string" ? e.patch : typeof e.newText == "string" ? e.newText : void 0;
		return /* @__PURE__ */ Z("details", {
			className: "paui-diff",
			children: [/* @__PURE__ */ Z("summary", { children: [/* @__PURE__ */ Z(fc, {}), n] }), r ? /* @__PURE__ */ Z("pre", { children: r }) : /* @__PURE__ */ Z("span", {
				className: "paui-muted",
				children: t.binaryChange
			})]
		});
	}
	return e.type === "terminal" ? /* @__PURE__ */ Z("span", {
		className: "paui-muted",
		children: [
			/* @__PURE__ */ Z(cc, {}),
			" ",
			t.terminalOutputInActivity
		]
	}) : /* @__PURE__ */ Z("span", {
		className: "paui-unsupported",
		children: t.unsupportedContent(typeof e.type == "string" ? e.type : t.toolResult)
	});
}
function vs() {
	let { controller: e, snapshot: t, labels: n, runAction: r, ids: i } = Q("ChatComposer"), [a, o] = F(""), [s, c] = F(0), [l, u] = F(!1), d = L(!1), f = L(null), p = Ls(t), m = L(p), h = L(/* @__PURE__ */ new Map()), g = t.activities.some((e) => e.type !== "notice") || t.interactions.length || t.phase === "auth_required" || t.error ? "docked" : "hero";
	I(() => {
		if (m.current !== p) {
			let e = m.current;
			h.current.set(e, a), m.current = p;
			let t = h.current.get(p);
			e === void 0 && t === void 0 && (t = a, h.current.set(p, a)), o(t ?? "");
		}
	}, [p, a]), et(() => {
		let e = f.current;
		e && (e.style.height = "0px", e.style.height = `${Math.min(e.scrollHeight, 336)}px`);
	}, [g, a]);
	let _ = !t.sessionId || t.phase === "connecting" || t.phase === "auth_required" || t.phase === "closed", v = t.phase === "running" || t.phase === "awaiting_user" || t.phase === "cancelling", y = () => {
		let t = a.trim();
		if (!t || _ || v) return;
		let n = p;
		h.current.set(n, ""), o(""), u(!0);
		try {
			e.send(t).done.catch(() => {
				h.current.get(n) || (h.current.set(n, t), m.current === n && o(t));
			});
		} catch {
			h.current.set(n, t), m.current === n && o(t);
		}
	}, b = a.startsWith("/") && !/\s/.test(a.slice(1)) && !l ? t.commands.filter((e) => e.name.startsWith(a.slice(1).split(/\s/, 1)[0] ?? "")).slice(0, 5) : [], x = Math.min(s, Math.max(0, b.length - 1)), S = (e) => {
		let t = `/${e} `;
		h.current.set(p, t), o(t), u(!0), f.current?.focus();
	}, ee = (e) => {
		if (!e.repeat) {
			if (b.length && e.key === "ArrowDown") {
				e.preventDefault(), c((x + 1) % b.length);
				return;
			}
			if (b.length && e.key === "ArrowUp") {
				e.preventDefault(), c((x - 1 + b.length) % b.length);
				return;
			}
			if (b.length && e.key === "Escape") {
				e.preventDefault(), u(!0);
				return;
			}
			if (e.key === "Enter" && !e.shiftKey && !d.current && !e.nativeEvent.isComposing) {
				e.preventDefault();
				let t = b[x];
				t ? S(t.name) : y();
			}
		}
	}, C = `${i.instance}-commands`;
	return /* @__PURE__ */ Z("footer", {
		className: "paui-composer-wrap",
		"data-pretty-aui-slot": "composer",
		"data-placement": g,
		children: [b.length ? /* @__PURE__ */ Z("div", {
			className: "paui-commands",
			role: "listbox",
			id: C,
			"aria-label": n.commands,
			children: b.map((e, t) => /* @__PURE__ */ Z("button", {
				type: "button",
				id: `${C}-${t}`,
				role: "option",
				"aria-selected": t === x,
				onMouseDown: (e) => e.preventDefault(),
				onClick: () => S(e.name),
				children: [/* @__PURE__ */ Z("code", { children: ["/", e.name] }), /* @__PURE__ */ Z("span", { children: e.description })]
			}, e.name))
		}) : null, /* @__PURE__ */ Z("div", {
			className: "paui-composer",
			"data-pretty-aui-slot": "composer-input",
			children: [
				t.contextSelection.items.length || t.contextSelection.canAdd ? /* @__PURE__ */ Z("div", {
					className: "paui-composer__context",
					"data-pretty-aui-slot": "composer-context",
					role: "group",
					"aria-label": n.contextSelection,
					children: [t.contextSelection.canAdd ? /* @__PURE__ */ Z("button", {
						className: "paui-context-add",
						type: "button",
						"aria-label": n.addContext,
						title: n.addContext,
						disabled: _ || v || t.contextSelection.busy,
						onMouseDown: (e) => e.preventDefault(),
						onClick: () => r(() => e.addContext()),
						children: /* @__PURE__ */ Z("span", {
							"aria-hidden": "true",
							children: "+"
						})
					}) : null, t.contextSelection.items.map((i) => /* @__PURE__ */ Z("span", {
						className: "paui-context-chip",
						"data-pretty-aui-slot": "composer-context-item",
						title: i.label,
						children: [/* @__PURE__ */ Z("span", {
							className: "paui-context-chip__label",
							children: i.label
						}), t.contextSelection.canRemove ? /* @__PURE__ */ Z("button", {
							type: "button",
							"aria-label": n.removeContext(i.label),
							title: n.removeContext(i.label),
							disabled: _ || v || t.contextSelection.busy,
							onMouseDown: (e) => e.preventDefault(),
							onClick: () => r(() => e.removeContext(i.id)),
							children: /* @__PURE__ */ Z("span", {
								"aria-hidden": "true",
								children: "×"
							})
						}) : null]
					}, i.id))]
				}) : null,
				/* @__PURE__ */ Z("textarea", {
					ref: f,
					rows: 1,
					value: a,
					disabled: _,
					placeholder: n.composerPlaceholder,
					"aria-label": n.composerPlaceholder,
					role: "combobox",
					"aria-autocomplete": "list",
					"aria-haspopup": "listbox",
					"aria-controls": b.length ? C : void 0,
					"aria-expanded": !!b.length,
					"aria-activedescendant": b.length ? `${C}-${x}` : void 0,
					onInput: (e) => {
						let t = e.currentTarget.value;
						h.current.set(p, t), o(t), c(0), u(!1);
					},
					onCompositionStart: () => {
						d.current = !0;
					},
					onCompositionEnd: () => {
						d.current = !1;
					},
					onKeyDown: ee
				}),
				/* @__PURE__ */ Z("div", {
					className: "paui-composer__actions",
					"data-pretty-aui-slot": "composer-actions",
					children: [t.configOptions.length ? /* @__PURE__ */ Z(ys, {
						controller: e,
						options: t.configOptions
					}) : /* @__PURE__ */ Z("span", {}), v ? /* @__PURE__ */ Z("button", {
						className: "paui-send paui-stop",
						type: "button",
						onMouseDown: (e) => e.preventDefault(),
						onClick: () => r(() => e.cancel()),
						disabled: t.phase === "cancelling",
						children: [/* @__PURE__ */ Z(Xs, {}), /* @__PURE__ */ Z("span", {
							className: "paui-sr-only",
							children: n.stop
						})]
					}) : /* @__PURE__ */ Z("button", {
						className: "paui-send",
						type: "button",
						onMouseDown: (e) => e.preventDefault(),
						onClick: y,
						disabled: _ || !a.trim(),
						children: [/* @__PURE__ */ Z(Ys, {}), /* @__PURE__ */ Z("span", {
							className: "paui-sr-only",
							children: n.send
						})]
					})]
				})
			]
		})]
	});
}
function ys({ controller: e, options: t }) {
	let { runAction: n } = Q("ChatComposer");
	return /* @__PURE__ */ Z("div", {
		className: "paui-config",
		children: t.map((t) => t.type === "boolean" ? /* @__PURE__ */ Z("label", {
			title: t.description,
			children: [/* @__PURE__ */ Z("input", {
				type: "checkbox",
				checked: !!t.currentValue,
				onChange: (r) => n(() => e.setConfigOption(t.id, r.target.checked))
			}), /* @__PURE__ */ Z("span", { children: t.name })]
		}, t.id) : t.type === "select" ? /* @__PURE__ */ Z(bs, {
			controller: e,
			option: t
		}, t.id) : null)
	});
}
function bs({ controller: e, option: t }) {
	let { runAction: n } = Q("ChatComposer"), r = L(null), i = L(null), a = L(null), o = `paui-config-${it().replaceAll(":", "")}`, s = t.options ?? [], c = s.findIndex((e) => e.value === String(t.currentValue)), l = c >= 0 ? s[c] : void 0, [u, d] = F(!1), [f, p] = F(Math.max(0, c)), m = (e = Math.max(0, c)) => {
		s.length && (p(e), d(!0));
	}, h = (e = !1) => {
		d(!1), e && i.current?.focus();
	}, g = (r) => {
		let i = s[r];
		i && (h(!0), i.value !== String(t.currentValue) && n(() => e.setConfigOption(t.id, i.value)));
	}, _ = (e) => {
		s.length && p((t) => (t + e + s.length) % s.length);
	};
	return I(() => {
		if (!u) return;
		let e = (e) => {
			r.current && e.composedPath().includes(r.current) || d(!1);
		};
		return window.addEventListener("pointerdown", e, !0), () => window.removeEventListener("pointerdown", e, !0);
	}, [u]), I(() => {
		u && (a.current?.querySelector(`#${o}-option-${f}`))?.scrollIntoView?.({ block: "nearest" });
	}, [
		f,
		o,
		u
	]), /* @__PURE__ */ Z("div", {
		className: "paui-config__field",
		ref: r,
		children: [/* @__PURE__ */ Z("button", {
			ref: i,
			className: "paui-config__trigger",
			type: "button",
			role: "combobox",
			"aria-label": t.name,
			"aria-controls": u ? o : void 0,
			"aria-expanded": u,
			"aria-haspopup": "listbox",
			"aria-activedescendant": u ? `${o}-option-${f}` : void 0,
			title: t.description,
			disabled: !s.length,
			onClick: () => u ? h() : m(),
			onKeyDown: (e) => {
				if (e.key === "ArrowDown" || e.key === "ArrowUp") {
					e.preventDefault();
					let t = e.key === "ArrowDown" ? 1 : -1;
					u ? _(t) : m(((c >= 0 ? c : 0) + t + s.length) % s.length);
					return;
				}
				if (e.key === "Home" && u) {
					e.preventDefault(), p(0);
					return;
				}
				if (e.key === "End" && u) {
					e.preventDefault(), p(Math.max(0, s.length - 1));
					return;
				}
				if (e.key === "Enter" || e.key === " ") {
					e.preventDefault(), u ? g(f) : m();
					return;
				}
				if (e.key === "Escape" && u) {
					e.preventDefault(), h(!0);
					return;
				}
				e.key === "Tab" && h();
			},
			children: [/* @__PURE__ */ Z("span", { children: l?.name ?? String(t.currentValue) }), /* @__PURE__ */ Z($s, {})]
		}), u ? /* @__PURE__ */ Z("div", {
			ref: a,
			className: "paui-config__listbox",
			id: o,
			role: "listbox",
			"aria-label": t.name,
			children: s.map((e, n) => /* @__PURE__ */ Z("button", {
				id: `${o}-option-${n}`,
				className: "paui-config__option",
				type: "button",
				role: "option",
				"aria-selected": e.value === String(t.currentValue),
				"data-active": n === f || void 0,
				title: e.description,
				tabIndex: -1,
				onMouseMove: n === f ? void 0 : () => p(n),
				onMouseDown: (e) => e.preventDefault(),
				onClick: () => g(n),
				children: [/* @__PURE__ */ Z("span", { children: e.name }), /* @__PURE__ */ Z("span", {
					className: "paui-config__check",
					"aria-hidden": "true",
					children: e.value === String(t.currentValue) ? /* @__PURE__ */ Z(ec, {}) : null
				})]
			}, e.value))
		}) : null]
	});
}
function xs({ interaction: e, controller: t, labels: n }) {
	let { ids: r } = Q("ChatInteractions"), i = `${r.instance}-${e.id}-title`;
	return /* @__PURE__ */ Z("section", {
		className: "paui-interaction",
		role: "alertdialog",
		"aria-labelledby": i,
		children: [/* @__PURE__ */ Z("div", {
			className: "paui-interaction__icon",
			children: /* @__PURE__ */ Z(lc, {})
		}), /* @__PURE__ */ Z("div", {
			className: "paui-interaction__content",
			children: [
				/* @__PURE__ */ Z("strong", {
					id: i,
					children: e.title || n.permission
				}),
				e.description ? /* @__PURE__ */ Z("p", { children: e.description }) : null,
				/* @__PURE__ */ Z("div", {
					className: "paui-interaction__actions",
					children: [e.options.map((n, r) => /* @__PURE__ */ Z("button", {
						type: "button",
						className: n.kind.startsWith("reject") ? "paui-button-secondary" : r === 0 ? "paui-button-primary" : "paui-button-secondary",
						onClick: () => t.respondPermission(e.id, {
							outcome: "selected",
							optionId: n.id
						}),
						children: n.name
					}, n.id)), /* @__PURE__ */ Z("button", {
						type: "button",
						className: "paui-button-ghost",
						onClick: () => t.respondPermission(e.id, { outcome: "cancelled" }),
						children: n.cancel
					})]
				})
			]
		})]
	});
}
function Ss({ interaction: e, controller: t, labels: n }) {
	let { ids: r } = Q("ChatInteractions"), i = `${r.instance}-${e.id}-title`;
	if (e.mode === "url" && e.url) {
		let r = Fs(e.url);
		return /* @__PURE__ */ Z("section", {
			className: "paui-interaction",
			role: "dialog",
			"aria-labelledby": i,
			children: [/* @__PURE__ */ Z("div", {
				className: "paui-interaction__icon",
				children: /* @__PURE__ */ Z(uc, {})
			}), /* @__PURE__ */ Z("div", {
				className: "paui-interaction__content",
				children: [
					/* @__PURE__ */ Z("strong", {
						id: i,
						children: e.message
					}),
					/* @__PURE__ */ Z("code", {
						className: "paui-url",
						children: e.url
					}),
					/* @__PURE__ */ Z("div", {
						className: "paui-interaction__actions",
						children: [
							/* @__PURE__ */ Z("button", {
								className: "paui-button-primary",
								type: "button",
								disabled: !r,
								onClick: () => r ? window.open(e.url, "_blank", "noopener,noreferrer") : void 0,
								children: n.openLink
							}),
							/* @__PURE__ */ Z("button", {
								className: "paui-button-secondary",
								type: "button",
								onClick: () => t.respondElicitation(e.id, { action: "accept" }),
								children: n.finish
							}),
							/* @__PURE__ */ Z("button", {
								className: "paui-button-ghost",
								type: "button",
								onClick: () => t.respondElicitation(e.id, { action: "decline" }),
								children: n.decline
							})
						]
					})
				]
			})]
		});
	}
	return /* @__PURE__ */ Z(Cs, {
		interaction: e,
		controller: t,
		labels: n,
		titleId: i
	});
}
function Cs({ interaction: e, controller: t, labels: n, titleId: r }) {
	let i = e.requestedSchema, a = Hs(i?.properties) ? i.properties : {}, o = Array.isArray(i?.required) ? i.required.filter((e) => typeof e == "string") : [];
	return /* @__PURE__ */ Z("form", {
		className: "paui-interaction paui-form",
		onSubmit: (n) => {
			n.preventDefault();
			let r = n.currentTarget, i = new FormData(r), o = {};
			for (let [e, t] of Object.entries(a)) if (Hs(t)) {
				if (t.type === "boolean") o[e] = i.get(e) === "on";
				else if (t.type === "number" || t.type === "integer") {
					let t = i.get(e);
					if (typeof t != "string" || t.trim() === "") continue;
					let n = Number(t);
					Number.isFinite(n) && (o[e] = n);
				} else o[e] = t.type === "array" ? i.getAll(e).map(String) : String(i.get(e) ?? "");
			}
			t.respondElicitation(e.id, {
				action: "accept",
				content: o
			});
		},
		"aria-labelledby": r,
		children: [/* @__PURE__ */ Z("div", {
			className: "paui-interaction__icon",
			children: /* @__PURE__ */ Z(_c, {})
		}), /* @__PURE__ */ Z("div", {
			className: "paui-interaction__content",
			children: [
				/* @__PURE__ */ Z("strong", {
					id: r,
					children: e.message
				}),
				/* @__PURE__ */ Z("div", {
					className: "paui-fields",
					children: Object.entries(a).map(([e, t]) => Hs(t) ? /* @__PURE__ */ Z(ws, {
						name: e,
						schema: t,
						required: o.includes(e)
					}, e) : null)
				}),
				/* @__PURE__ */ Z("div", {
					className: "paui-interaction__actions",
					children: [/* @__PURE__ */ Z("button", {
						className: "paui-button-primary",
						type: "submit",
						children: n.accept
					}), /* @__PURE__ */ Z("button", {
						className: "paui-button-ghost",
						type: "button",
						onClick: () => t.respondElicitation(e.id, { action: "decline" }),
						children: n.decline
					})]
				})
			]
		})]
	});
}
function ws({ name: e, schema: t, required: n }) {
	let r = typeof t.title == "string" ? t.title : e, i = typeof t.description == "string" ? t.description : void 0, a = Array.isArray(t.enum) ? t.enum.filter((e) => typeof e == "string") : [];
	return t.type === "boolean" ? /* @__PURE__ */ Z("label", {
		className: "paui-field paui-field--check",
		children: [/* @__PURE__ */ Z("input", {
			name: e,
			type: "checkbox"
		}), /* @__PURE__ */ Z("span", { children: r })]
	}) : a.length ? /* @__PURE__ */ Z("label", {
		className: "paui-field",
		children: [
			/* @__PURE__ */ Z("span", { children: r }),
			/* @__PURE__ */ Z("select", {
				name: e,
				required: n,
				children: a.map((e) => /* @__PURE__ */ Z("option", { children: e }, e))
			}),
			i ? /* @__PURE__ */ Z("small", { children: i }) : null
		]
	}) : /* @__PURE__ */ Z("label", {
		className: "paui-field",
		children: [
			/* @__PURE__ */ Z("span", { children: r }),
			/* @__PURE__ */ Z("input", {
				name: e,
				required: n,
				type: t.type === "number" || t.type === "integer" ? "number" : "text"
			}),
			i ? /* @__PURE__ */ Z("small", { children: i }) : null
		]
	});
}
function Ts() {
	let { controller: e, snapshot: t, labels: n, runAction: r } = Q("ChatInteractions");
	return /* @__PURE__ */ Z("section", {
		className: "paui-auth",
		children: [
			/* @__PURE__ */ Z(lc, {}),
			/* @__PURE__ */ Z("strong", { children: n.authRequired }),
			/* @__PURE__ */ Z("div", { children: t.authMethods.map((t) => /* @__PURE__ */ Z("button", {
				type: "button",
				onClick: () => r(() => e.authenticate(t.id)),
				children: t.name
			}, t.id)) })
		]
	});
}
function Es({ controller: e, snapshot: t, labels: n, onClose: r }) {
	let { ids: i } = Q("ChatHeader"), a = L(null), o = L(null), s = L(null), c = L(null), l = L(null), [u, d] = F(!1), [f, p] = F(), [m, h] = F(), [g, _] = F(), v = Ds(t), y = v.find((e) => e.sessionId === m), b = Date.now(), x = u || y?.loaded?.phase === "running" || y?.loaded?.phase === "cancelling" || (y?.loaded?.interactionCount ?? 0) > 0, S = nt((e = !1) => {
		let t = l.current;
		h(void 0), _(void 0), e && t?.isConnected && t.focus();
	}, []);
	I(() => {
		let e = Os(o.current), t = e instanceof HTMLElement ? e : void 0;
		return a.current?.focus(), () => {
			t?.isConnected && t.focus();
		};
	}, []), I(() => {
		t.capabilities.listSessions && !t.sessions && (d(!0), e.listSessions().catch((e) => p(e instanceof Error ? e.message : String(e))).finally(() => d(!1)));
	}, [
		e,
		t.capabilities.listSessions,
		t.sessions
	]), et(() => {
		if (!m) return;
		let e = o.current, t = s.current, n = l.current;
		if (!e || !t || !n) return;
		let r = e.getBoundingClientRect(), i = t.getBoundingClientRect(), a = n.getBoundingClientRect(), c = Math.max(8, r.width - i.width - 8), u = Math.min(Math.max(a.right - r.left - i.width, 8), c), d = a.bottom - r.top + 4, f = a.top - r.top - i.height - 4, p = d + i.height <= r.height - 8 ? d : f, h = Math.max(8, r.height - i.height - 8);
		_({
			left: u,
			top: Math.min(Math.max(p, 8), h)
		});
	}, [m]), et(() => {
		m && g && c.current?.focus();
	}, [g, m]), I(() => {
		if (!m) return;
		let e = (e) => {
			let t = e.composedPath();
			s.current && t.includes(s.current) || l.current && t.includes(l.current) || S();
		}, t = () => S();
		return window.addEventListener("pointerdown", e, !0), window.addEventListener("scroll", t, !0), window.addEventListener("resize", t), () => {
			window.removeEventListener("pointerdown", e, !0), window.removeEventListener("scroll", t, !0), window.removeEventListener("resize", t);
		};
	}, [S, m]), I(() => {
		let e = (e) => {
			if (e.key === "Escape") {
				if (e.preventDefault(), m) {
					e.stopPropagation(), S(!0);
					return;
				}
				r();
				return;
			}
			if (e.key !== "Tab") return;
			let t = o.current ? [...o.current.querySelectorAll(As)].filter((e) => !e.hasAttribute("disabled")) : [], n = t[0], i = t.at(-1);
			if (!n || !i) return;
			let a = Os(o.current);
			e.shiftKey && a === n ? (e.preventDefault(), i.focus()) : (!e.shiftKey && a === i || !a || !o.current?.contains(a)) && (e.preventDefault(), n.focus());
		};
		return window.addEventListener("keydown", e, !0), () => window.removeEventListener("keydown", e, !0);
	}, [
		S,
		m,
		r
	]);
	let ee = async (t) => {
		d(!0), p(void 0);
		try {
			await e.openSession(t), r();
		} catch (e) {
			p(e instanceof Error ? e.message : String(e));
		} finally {
			d(!1);
		}
	}, C = async (t) => {
		d(!0), p(void 0);
		try {
			await e.listSessions(t);
		} catch (e) {
			p(e instanceof Error ? e.message : String(e));
		} finally {
			d(!1);
		}
	}, w = async (t) => {
		let r = t.title ?? n.sessionUntitled;
		if (!window.confirm(n.confirmDeleteSession(r))) {
			S(!0);
			return;
		}
		S(), d(!0), p(void 0);
		try {
			await e.deleteSession(t.sessionId);
		} catch (e) {
			p(e instanceof Error ? e.message : String(e));
		} finally {
			d(!1);
		}
	};
	return /* @__PURE__ */ Z("div", {
		className: "paui-drawer-backdrop",
		role: "presentation",
		onMouseDown: (e) => {
			e.target === e.currentTarget && r();
		},
		children: /* @__PURE__ */ Z("aside", {
			ref: o,
			className: "paui-drawer",
			role: "dialog",
			"aria-modal": "true",
			"aria-labelledby": i.sessionsTitle,
			children: [
				/* @__PURE__ */ Z("header", { children: [/* @__PURE__ */ Z("strong", {
					id: i.sessionsTitle,
					children: n.sessions
				}), /* @__PURE__ */ Z("button", {
					ref: a,
					className: "paui-icon-button",
					type: "button",
					onClick: r,
					children: [/* @__PURE__ */ Z(Ks, {}), /* @__PURE__ */ Z("span", {
						className: "paui-sr-only",
						children: n.close
					})]
				})] }),
				/* @__PURE__ */ Z("div", {
					className: "paui-session-list",
					children: [
						u && !t.sessions ? /* @__PURE__ */ Z("span", {
							className: "paui-muted",
							children: "…"
						}) : null,
						!u && !v.length ? /* @__PURE__ */ Z("span", {
							className: "paui-muted",
							children: n.noSessions
						}) : null,
						v.map((e) => {
							let r = e.sessionId === t.sessionId, a = e.title ?? n.sessionUntitled, o = t.capabilities.deleteSession && !r, s = e.sessionId === m;
							return /* @__PURE__ */ Z("div", {
								className: "paui-session",
								"data-active": r || void 0,
								"data-has-actions": o || void 0,
								"data-loaded": e.loaded !== void 0 || void 0,
								"data-menu-open": s || void 0,
								children: [/* @__PURE__ */ Z("button", {
									className: "paui-session__select",
									type: "button",
									"aria-current": r ? "page" : void 0,
									disabled: u || r,
									onClick: () => void ee(e.sessionId),
									children: [e.loaded?.phase === "running" ? /* @__PURE__ */ Z("span", {
										className: "paui-session__spinner",
										"aria-hidden": "true"
									}) : null, /* @__PURE__ */ Z("strong", {
										className: "paui-session__title",
										children: a
									})]
								}), /* @__PURE__ */ Z("span", {
									className: "paui-session__trailing",
									children: [/* @__PURE__ */ Z("span", {
										className: "paui-session__meta",
										children: [/* @__PURE__ */ Z("span", { children: e.loaded ? n.sessionPhase(e.loaded.phase) : Vs(e.updatedAt, b, n.sessionAge) }), e.loaded?.interactionCount ? /* @__PURE__ */ Z(O, { children: [/* @__PURE__ */ Z("span", {
											className: "paui-session__meta-separator",
											"aria-hidden": "true",
											children: "·"
										}), /* @__PURE__ */ Z("span", { children: n.pendingInteractions(e.loaded.interactionCount) })] }) : null]
									}), o ? /* @__PURE__ */ Z("button", {
										className: "paui-session__action",
										type: "button",
										"aria-controls": s ? `${i.instance}-session-menu` : void 0,
										"aria-expanded": s,
										"aria-haspopup": "menu",
										"aria-label": n.sessionActions(a),
										disabled: u,
										onClick: (t) => {
											if (t.stopPropagation(), s) {
												S(!0);
												return;
											}
											l.current = t.currentTarget, _(void 0), h(e.sessionId);
										},
										children: /* @__PURE__ */ Z(qs, {})
									}) : null]
								})]
							}, e.sessionId);
						}),
						t.sessions?.nextCursor ? /* @__PURE__ */ Z("button", {
							className: "paui-load-more",
							type: "button",
							disabled: u,
							onClick: () => void C(t.sessions?.nextCursor),
							children: n.loadMore
						}) : null,
						f ? /* @__PURE__ */ Z("span", {
							className: "paui-error-text",
							role: "alert",
							children: f
						}) : null
					]
				}),
				y && t.capabilities.deleteSession && y.sessionId !== t.sessionId ? /* @__PURE__ */ Z("div", {
					ref: s,
					id: `${i.instance}-session-menu`,
					className: "paui-session-menu",
					role: "menu",
					"aria-label": n.sessionActions(y.title ?? n.sessionUntitled),
					style: g ?? { visibility: "hidden" },
					children: /* @__PURE__ */ Z("button", {
						ref: c,
						type: "button",
						role: "menuitem",
						"aria-disabled": x,
						onClick: () => {
							x || w(y);
						},
						children: [/* @__PURE__ */ Z(Js, {}), /* @__PURE__ */ Z("span", { children: n.deleteSession })]
					})
				}) : null
			]
		})
	});
}
function Ds(e) {
	let t = new Map((e.sessions?.sessions ?? []).map((e) => [e.sessionId, e])), n = new Set(e.loadedSessions.map((e) => e.sessionId));
	return [...e.loadedSessions.map((e) => ({
		...t.get(e.sessionId),
		...e,
		loaded: e
	})), ...(e.sessions?.sessions ?? []).filter((e) => !n.has(e.sessionId))];
}
function Os(e) {
	let t = e?.getRootNode();
	return t instanceof Document || t instanceof ShadowRoot ? t.activeElement : document.activeElement;
}
var ks = new Sa({
	gfm: !0,
	breaks: !0
}), As = "a[href], button, input, select, textarea, [tabindex]:not([tabindex=\"-1\"])", js = new va();
js.html = ({ text: e }) => Ps(e), js.image = ({ text: e }) => `<span class="paui-markdown-image-alt">${Ps(e)}</span>`, js.checkbox = ({ checked: e }) => e ? "[x] " : "[ ] ", js.link = ({ href: e, title: t, tokens: n }) => {
	let r = Ps(n.map((e) => e.raw).join(""));
	return Fs(e) ? `<a href="${Ns(e)}" target="_blank" rel="noopener noreferrer"${t ? ` title="${Ns(t)}"` : ""}>${r}</a>` : r;
}, ks.use({ renderer: js });
function Ms(e) {
	let t = ks.parse(e);
	return Vr.sanitize(t, {
		USE_PROFILES: { html: !0 },
		ADD_ATTR: ["target", "rel"],
		FORBID_TAGS: [
			"style",
			"form",
			"input",
			"button",
			"textarea",
			"select",
			"option"
		],
		FORBID_ATTR: ["style"]
	});
}
function Ns(e) {
	return Ps(e).replaceAll("\"", "&quot;").replaceAll("'", "&#39;");
}
function Ps(e) {
	return e.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}
function Fs(e) {
	try {
		let t = new URL(e, globalThis.location?.href ?? "https://example.invalid");
		return [
			"http:",
			"https:",
			"mailto:"
		].includes(t.protocol);
	} catch {
		return !1;
	}
}
function Is(e) {
	let t = No.get(e);
	if (t !== void 0) return t;
	let n = ++Po;
	return No.set(e, n), n;
}
function Ls(e) {
	if (e.sessionId) return e.sessionInstanceId ? `${e.sessionId}\u0000${e.sessionInstanceId}` : e.sessionId;
}
function Rs(e, t) {
	if (typeof globalThis.requestAnimationFrame != "function") return e.subscribe(t);
	let n, r = e.getSnapshot(), i = e.subscribe(() => {
		let i = e.getSnapshot(), a = r.phase === "running" && i.phase === "running";
		if (r = i, !a) {
			n !== void 0 && (typeof globalThis.cancelAnimationFrame == "function" && globalThis.cancelAnimationFrame(n), n = void 0), t();
			return;
		}
		n === void 0 && (n = globalThis.requestAnimationFrame(() => {
			n = void 0, t();
		}));
	});
	return () => {
		i(), n !== void 0 && typeof globalThis.cancelAnimationFrame == "function" && globalThis.cancelAnimationFrame(n);
	};
}
function zs(e) {
	return e.some((e) => e.status === "in_progress") ? "in_progress" : e.length && e.every((e) => e.status === "completed") ? "completed" : "pending";
}
function Bs(e) {
	switch (e.type) {
		case "tool": return e.status;
		case "plan": return zs(e.entries);
		case "terminal": return e.exited ? "completed" : "in_progress";
		case "message": return e.pending ? "pending" : void 0;
		case "unsupported": return "unsupported";
		case "context":
		case "notice": return;
	}
}
function Vs(e, t = Date.now(), n = Ta.sessionAge) {
	if (!e) return "";
	let r = new Date(e).valueOf();
	if (Number.isNaN(r)) return e;
	let i = 6e4, a = 60 * i, o = 24 * a, s = Math.max(0, t - r);
	return s < i ? n(0, "now") : s < a ? n(Math.floor(s / i), "minute") : s < o ? n(Math.floor(s / a), "hour") : s < 30 * o ? n(Math.floor(s / o), "day") : s < 365 * o ? n(Math.floor(s / (30 * o)), "month") : n(Math.floor(s / (365 * o)), "year");
}
function Hs(e) {
	return typeof e == "object" && !!e && !Array.isArray(e);
}
function Us({ status: e }) {
	return /* @__PURE__ */ Z("span", {
		className: "paui-status",
		"data-status": e,
		children: e.replaceAll("_", " ")
	});
}
function $({ children: e }) {
	return /* @__PURE__ */ Z("svg", {
		viewBox: "0 0 20 20",
		"aria-hidden": "true",
		focusable: "false",
		children: e
	});
}
var Ws = () => /* @__PURE__ */ Z($, { children: /* @__PURE__ */ Z("path", { d: "M3 10a7 7 0 1 0 2-4.9M3 3v4h4M10 6v4l3 2" }) }), Gs = () => /* @__PURE__ */ Z($, { children: /* @__PURE__ */ Z("path", { d: "M4 4h8a3 3 0 0 1 3 3v4a3 3 0 0 1-3 3H8l-4 3v-3a3 3 0 0 1-1-2V7a3 3 0 0 1 3-3M10 7v5M7.5 9.5h5" }) }), Ks = () => /* @__PURE__ */ Z($, { children: /* @__PURE__ */ Z("path", { d: "m5 5 10 10M15 5 5 15" }) }), qs = () => /* @__PURE__ */ Z($, { children: [
	/* @__PURE__ */ Z("circle", {
		cx: "5",
		cy: "10",
		r: "1",
		fill: "currentColor",
		stroke: "none"
	}),
	/* @__PURE__ */ Z("circle", {
		cx: "10",
		cy: "10",
		r: "1",
		fill: "currentColor",
		stroke: "none"
	}),
	/* @__PURE__ */ Z("circle", {
		cx: "15",
		cy: "10",
		r: "1",
		fill: "currentColor",
		stroke: "none"
	})
] }), Js = () => /* @__PURE__ */ Z($, { children: /* @__PURE__ */ Z("path", { d: "M4 6h12M8 3h4l1 3M6 6l1 11h6l1-11M9 9v5M12 9v5" }) }), Ys = () => /* @__PURE__ */ Z("svg", {
	viewBox: "0 0 16 16",
	"aria-hidden": "true",
	focusable: "false",
	children: /* @__PURE__ */ Z("path", {
		d: "M8.3125.9802c.3552.0729.6665.224 0.9502.4521.2245.1807.4676.4256.7168.6748L14.707 6.8347 13.293 8.2487 9 3.9558v11.0859H7V3.9558L2.707 8.2487 1.293 6.8347l4.7275-4.7276c.2492-.2492.4923-.4941.7168-.6748.2393-.1924.5471-.3883.9502-.4521.2098-.0332.4156-.025.625 0Z",
		fill: "currentColor"
	})
}), Xs = () => /* @__PURE__ */ Z("svg", {
	viewBox: "0 0 16 16",
	"aria-hidden": "true",
	focusable: "false",
	children: /* @__PURE__ */ Z("rect", {
		x: "3",
		y: "3",
		width: "10",
		height: "10",
		rx: "3",
		fill: "currentColor"
	})
}), Zs = () => /* @__PURE__ */ Z($, { children: /* @__PURE__ */ Z("path", { d: "m5 8 5 5 5-5" }) }), Qs = () => /* @__PURE__ */ Z($, { children: /* @__PURE__ */ Z("path", { d: "m12.5 4.5-5 5 5 5" }) }), $s = () => /* @__PURE__ */ Z("svg", {
	viewBox: "0 0 14 14",
	"aria-hidden": "true",
	focusable: "false",
	children: /* @__PURE__ */ Z("path", { d: "m4 5.5 3 3 3-3" })
}), ec = () => /* @__PURE__ */ Z("svg", {
	viewBox: "0 0 14 14",
	"aria-hidden": "true",
	focusable: "false",
	children: /* @__PURE__ */ Z("path", { d: "m3 7 2.5 2.5L11 4" })
}), tc = () => /* @__PURE__ */ Z($, { children: /* @__PURE__ */ Z("path", { d: "M12.5 4.2a4 4 0 0 0-5 5L3 13.7 6.3 17l4.5-4.5a4 4 0 0 0 5-5l-2.3 2.3-3.3-3.3 2.3-2.3Z" }) }), nc = () => /* @__PURE__ */ Z($, { children: [
	/* @__PURE__ */ Z("circle", {
		cx: "10",
		cy: "5",
		r: "2"
	}),
	/* @__PURE__ */ Z("circle", {
		cx: "5",
		cy: "14",
		r: "2"
	}),
	/* @__PURE__ */ Z("circle", {
		cx: "15",
		cy: "14",
		r: "2"
	}),
	/* @__PURE__ */ Z("path", { d: "m8.8 6.7-2.6 5.6M11.2 6.7l2.6 5.6M7 14h6" })
] }), rc = () => /* @__PURE__ */ Z($, { children: /* @__PURE__ */ Z("path", { d: "M5 5h5v5M10 5 4.5 10.5M9 9h6v6H9" }) }), ic = () => /* @__PURE__ */ Z($, { children: /* @__PURE__ */ Z("path", { d: "M6 5h10M6 10h10M6 15h10M3 5h.01M3 10h.01M3 15h.01" }) }), ac = () => /* @__PURE__ */ Z("svg", {
	className: "paui-think-icon",
	viewBox: "0 0 14 14",
	"aria-hidden": "true",
	focusable: "false",
	children: [/* @__PURE__ */ Z("path", {
		d: "M7.06431 5.93342C7.68763 5.93342 8.19307 6.43904 8.19322 7.06233C8.19322 7.68573 7.68772 8.19123 7.06431 8.19123C6.44099 8.19113 5.9354 7.68567 5.9354 7.06233C5.93555 6.43911 6.44108 5.93353 7.06431 5.93342Z",
		fill: "currentColor"
	}), /* @__PURE__ */ Z("path", {
		fillRule: "evenodd",
		clipRule: "evenodd",
		d: "M8.6815.963693c1.4354-.516674 2.9451-.588864 3.8818.347657.9367.9367.8644 2.44641.3477 3.88184-.1984.55112-.4724 1.12477-.8145 1.7041.4004.64909.7176 1.29289.9395 1.90918.5167 1.43543.5891 2.94513-.3477 3.88183-.9367.9367-2.4463.8644-3.8818.3477-.61628-.2219-1.26009-.5391-1.90918-.9395-.57935.3421-1.15297.616-1.7041.8145-1.43545.5166-2.94512.589-3.88184-.3477-.936521-.9367-.864331-2.4465-.347656-3.88188.208126-.57809.499486-1.18084.865236-1.78907-.30714-.53529-.55661-1.06415-.74024-1.57421C.572068 3.88278.499714 2.37306 1.43638 1.43635c.9367-.936695 2.44642-.864306 3.88184-.34766.51006.18363 1.03893.43311 1.57421.74024.60823-.36575 1.21098-.65712 1.78907-.865237ZM11.3573 8.01154c-.449.61099-.9672 1.21719-1.54787 1.79786-.58066.5807-1.18688 1.0989-1.79785 1.5478.41412.2269.81712.4115 1.20117.5499 1.33285.4797 2.21185.3476 2.62695-.0674.4151-.4151.5472-1.2941.0674-2.62698-.1383-.38406-.323-.78704-.5498-1.20118ZM2.56529 8.02912c-.19185.3641-.35034.71884-.47266 1.0586-.47972 1.33268-.34751 2.21178.06738 2.62698.41504.415 1.29414.5471 2.62696.0674.3236-.1165.66089-.2657 1.00683-.4454-.5448-.4144-1.08458-.8834-1.60351-1.4023-.61451-.61453-1.1586-1.25807-1.625-1.90528Zm4.34179-4.78222c-.66643.45789-1.34248 1.01631-1.99316 1.66699-.65067.65067-1.2091 1.32674-1.66699 1.99316.47981.7262 1.08084 1.46754 1.79199 2.17871.61051.61051 1.24291 1.14074 1.86914 1.58204.68562-.4653 1.38274-1.03704 2.05273-1.70704.67001-.67001 1.24171-1.3671 1.70701-2.05273-.4413-.62623-.97149-1.25863-1.58201-1.86914-.71117-.71116-1.45251-1.31217-2.17871-1.79199Zm4.80762-1.08692c-.4151-.41489-1.2943-.5471-2.62695-.06738-.3394.12219-.69393.28011-1.05762.47168.64715.46637 1.28982 1.01152 1.9043 1.62598.51897.51894.98787 1.0587 1.40237 1.60351.1796-.34592.3288-.68325.4453-1.00683.4797-1.33278.3476-2.21192-.0674-2.62696ZM4.91197 2.2176c-1.33275-.47972-2.21193-.34765-2.62696.06738-.415.41505-.5471 1.29422-.06738 2.62696.09946.27628.22349.56233.36914.85546.43254-.5787.92797-1.1516 1.47852-1.70214.55055-.55056 1.12343-1.04598 1.70214-1.47852-.29312-.14564-.57919-.26968-.85546-.36914Z",
		fill: "currentColor"
	})]
}), oc = () => /* @__PURE__ */ Z($, { children: /* @__PURE__ */ Z("path", { d: "M5 3h10v14H5zM8 7h4M8 10h4" }) }), sc = () => /* @__PURE__ */ Z($, { children: [/* @__PURE__ */ Z("circle", {
	cx: "8.5",
	cy: "8.5",
	r: "5.5"
}), /* @__PURE__ */ Z("path", { d: "m12.5 12.5 4 4" })] }), cc = () => /* @__PURE__ */ Z($, { children: /* @__PURE__ */ Z("path", { d: "m4 6 4 4-4 4M10 14h6" }) }), lc = () => /* @__PURE__ */ Z($, { children: /* @__PURE__ */ Z("path", { d: "M10 2 16 5v5c0 4-2.5 6.5-6 8-3.5-1.5-6-4-6-8V5l6-3Zm-2 8 1.5 1.5L13 8" }) }), uc = () => /* @__PURE__ */ Z($, { children: /* @__PURE__ */ Z("path", { d: "M8 12 12 8M6.5 13.5l-1 1a3 3 0 0 1-4-4l3-3a3 3 0 0 1 4 0M13.5 6.5l1-1a3 3 0 0 1 4 4l-3 3a3 3 0 0 1-4 0" }) }), dc = () => /* @__PURE__ */ Z($, { children: /* @__PURE__ */ Z("path", { d: "M5 2h7l4 4v12H5V2Zm7 0v5h4" }) }), fc = () => /* @__PURE__ */ Z($, { children: /* @__PURE__ */ Z("path", { d: "M5 3v14M3 5l2-2 2 2M15 17V3M13 15l2 2 2-2M9 7h3M9 13h3" }) }), pc = () => /* @__PURE__ */ Z($, { children: /* @__PURE__ */ Z("path", { d: "M6 5h10v10H6zM3 8v9h9" }) }), mc = () => /* @__PURE__ */ Z($, { children: [/* @__PURE__ */ Z("circle", {
	cx: "10",
	cy: "10",
	r: "7"
}), /* @__PURE__ */ Z("path", { d: "M10 9v5M10 6h.01" })] }), hc = () => /* @__PURE__ */ Z($, { children: [/* @__PURE__ */ Z("path", { d: "M10 2 19 18H1L10 2Z" }), /* @__PURE__ */ Z("path", { d: "M10 7v5M10 15h.01" })] }), gc = () => /* @__PURE__ */ Z($, { children: /* @__PURE__ */ Z("path", { d: "m10 2 1.5 4.5L16 8l-4.5 1.5L10 14l-1.5-4.5L4 8l4.5-1.5L10 2ZM15.5 13l.7 2.3 2.3.7-2.3.7-.7 2.3-.7-2.3-2.3-.7 2.3-.7.7-2.3Z" }) }), _c = () => /* @__PURE__ */ Z($, { children: /* @__PURE__ */ Z("path", { d: "M4 3h12v14H4zM7 7h6M7 10h6M7 13h3" }) }), vc = ".pretty-aui-standalone-root{box-sizing:border-box;width:100%;min-width:0;height:100%;min-height:0}.pretty-aui-standalone-root>.pretty-aui{height:100%;min-height:0}.pretty-aui{--paui-default-background:#fff;--paui-default-surface:#f7f8fa;--paui-default-surface-raised:#fff;--paui-default-user-bubble:#edf3fe;--paui-default-text:#0f1115;--paui-default-text-muted:#667085;--paui-default-border:#e5e7eb;--paui-default-accent:#4176e6;--paui-default-on-accent:#fff;--paui-default-accent-soft:#edf3fe;--paui-default-danger:#c63d4f;--paui-default-warning:#a86610;--paui-default-success:#24845b;--paui-default-action-hover:#679efe;--paui-default-flow-title:#61666b;--paui-default-flow-copy:#81858c;--paui-default-flow-caption:#adb2b8;--paui-background:var(--pretty-aui-color-background,var(--paui-default-background));--paui-surface:var(--pretty-aui-color-surface,var(--paui-default-surface));--paui-surface-raised:var(--pretty-aui-color-surface-raised,var(--paui-default-surface-raised));--paui-user-bubble:var(--pretty-aui-color-user-bubble,var(--paui-default-user-bubble));--paui-text:var(--pretty-aui-color-text,var(--paui-default-text));--paui-text-muted:var(--pretty-aui-color-text-muted,var(--paui-default-text-muted));--paui-border:var(--pretty-aui-color-border,var(--paui-default-border));--paui-accent:var(--pretty-aui-color-accent,var(--paui-default-accent));--paui-on-accent:var(--pretty-aui-color-on-accent,var(--paui-default-on-accent));--paui-accent-soft:var(--pretty-aui-color-accent-soft,var(--paui-default-accent-soft));--paui-danger:var(--pretty-aui-color-danger,var(--paui-default-danger));--paui-warning:var(--pretty-aui-color-warning,var(--paui-default-warning));--paui-success:var(--pretty-aui-color-success,var(--paui-default-success));--paui-action-hover:var(--paui-default-action-hover);--paui-flow-title:var(--pretty-aui-color-text-muted,var(--paui-default-flow-title));--paui-flow-copy:var(--pretty-aui-color-text-muted,var(--paui-default-flow-copy));--paui-flow-caption:var(--pretty-aui-color-text-muted,var(--paui-default-flow-caption));--paui-sans:var(--pretty-aui-font-sans,Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif);--paui-mono:var(--pretty-aui-font-mono,ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace);--paui-shadow-raised:var(--pretty-aui-shadow-raised,0 4px 12px 0 #00000005, 0 2px 8px 0 #0000000a);--paui-content-width:var(--pretty-aui-content-max-width,748px);--paui-composer-width:var(--pretty-aui-composer-max-width,780px);--paui-gutter:var(--pretty-aui-gutter,16px);box-sizing:border-box;width:100%;height:var(--pretty-aui-height,680px);min-width:0;min-height:var(--pretty-aui-min-height,420px);border:1px solid var(--paui-border);color:var(--paui-text);--lightningcss-light:initial;--lightningcss-dark: ;color-scheme:light;background:var(--paui-background);contain:layout style;font-family:var(--paui-sans);text-align:left;isolation:isolate;border-radius:14px;flex-direction:column;font-size:14px;line-height:1.5;display:flex;position:relative;overflow:clip;container:pretty-aui/inline-size}.pretty-aui[data-scheme=dark]{--paui-default-background:#151517;--paui-default-surface:#232324;--paui-default-surface-raised:#2c2c2e;--paui-default-user-bubble:#2c2c2e;--paui-default-text:#f9fafb;--paui-default-text-muted:#a4a7ae;--paui-default-border:#343438;--paui-default-accent:#679efe;--paui-default-on-accent:#0f1115;--paui-default-accent-soft:#202c43;--paui-default-danger:#f08a96;--paui-default-warning:#e6ab5e;--paui-default-success:#65c99c;--paui-default-action-hover:#8ab4ff;--paui-default-flow-title:#cfd3d6;--paui-default-flow-copy:#adb2b8;--paui-default-flow-caption:#81858c;--lightningcss-light: ;--lightningcss-dark:initial;color-scheme:dark}@media (prefers-color-scheme:dark){.pretty-aui[data-scheme=system]{--paui-default-background:#151517;--paui-default-surface:#232324;--paui-default-surface-raised:#2c2c2e;--paui-default-user-bubble:#2c2c2e;--paui-default-text:#f9fafb;--paui-default-text-muted:#a4a7ae;--paui-default-border:#343438;--paui-default-accent:#679efe;--paui-default-on-accent:#0f1115;--paui-default-accent-soft:#202c43;--paui-default-danger:#f08a96;--paui-default-warning:#e6ab5e;--paui-default-success:#65c99c;--paui-default-action-hover:#8ab4ff;--paui-default-flow-title:#cfd3d6;--paui-default-flow-copy:#adb2b8;--paui-default-flow-caption:#81858c;--lightningcss-light: ;--lightningcss-dark:initial;color-scheme:dark}}.pretty-aui *,.pretty-aui :before,.pretty-aui :after{box-sizing:border-box}.pretty-aui button,.pretty-aui input,.pretty-aui select,.pretty-aui textarea{color:inherit;font:inherit}.pretty-aui button{cursor:pointer}.pretty-aui :is(button,input,select,textarea):disabled{cursor:not-allowed;opacity:.46}.pretty-aui :is(button,input,select,textarea,summary,a,.paui-body,.paui-context-injection__body):focus-visible{outline:2px solid var(--paui-accent);outline-offset:2px}.pretty-aui svg{fill:none;stroke:currentColor;stroke-linecap:round;stroke-linejoin:round;stroke-width:1.6px;flex:none;width:18px;height:18px}.paui-header{z-index:4;border-bottom:1px solid var(--paui-border);background:color-mix(in srgb, var(--paui-background) 94%, transparent);-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px);justify-content:space-between;align-items:center;min-width:0;min-height:56px;padding:10px 14px 10px 18px;display:flex}.pretty-aui[data-surface=sidebar] .paui-header{min-height:48px;padding:7px 8px 7px 12px}.paui-identity,.paui-header__actions,.paui-interaction__actions,.paui-config{align-items:center;display:flex}.paui-identity{flex:auto;gap:10px;min-width:0}.paui-identity>div{min-width:0;display:grid}.paui-identity strong{letter-spacing:-.01em;text-overflow:ellipsis;white-space:nowrap;font-size:13px;font-weight:600;overflow:hidden}.paui-lineage{min-width:0;display:grid}.paui-lineage__titles{white-space:nowrap;align-items:center;gap:6px;min-width:0;display:flex}.paui-lineage__titles strong{text-overflow:ellipsis;min-width:0;overflow:hidden}.paui-lineage__ancestor{min-width:0;color:var(--paui-flow-caption);align-items:center;gap:6px;display:inline-flex}.paui-lineage__ancestor button{max-width:144px;color:var(--paui-text-muted);text-overflow:ellipsis;white-space:nowrap;background:0 0;border:0;padding:0;font-size:13px;overflow:hidden}.paui-lineage__ancestor button:hover:not(:disabled){color:var(--paui-text)}.paui-lineage__back{background:0 0;border:0;border-radius:7px;place-items:center;width:28px;height:28px;padding:0;display:none}.paui-lineage__back:hover:not(:disabled){background:var(--paui-surface)}.paui-lineage__back svg{width:16px;height:16px}.paui-protocol{color:var(--paui-text-muted);font-family:var(--paui-mono);letter-spacing:.02em;text-overflow:ellipsis;text-transform:uppercase;white-space:nowrap;font-size:10px;overflow:hidden}.pretty-aui[data-surface=sidebar] .paui-protocol{display:none}.paui-presence{border:2px solid var(--paui-background);background:var(--paui-text-muted);width:9px;height:9px;box-shadow:0 0 0 1px var(--paui-border);border-radius:50%;flex:none}.paui-presence[data-phase=idle]{background:var(--paui-success)}.paui-presence:is([data-phase=running],[data-phase=awaiting_user],[data-phase=cancelling]){background:var(--paui-accent);box-shadow:0 0 0 1px var(--paui-accent), 0 0 0 4px var(--paui-accent-soft)}.paui-header__actions{flex:none;gap:2px}.paui-icon-button,.paui-send,.paui-to-bottom{background:0 0;border:0;border-radius:10px;place-items:center;width:34px;height:34px;padding:0;display:inline-grid}.paui-icon-button:hover:not(:disabled){background:var(--paui-surface)}.paui-body{min-width:0;min-height:0;padding:24px var(--paui-gutter) 0;overscroll-behavior:contain;scrollbar-color:var(--paui-border) transparent;scrollbar-gutter:stable;flex:auto;position:relative;overflow:hidden auto}.paui-transcript{width:100%;max-width:var(--paui-content-width);gap:28px;margin:0 auto;padding-bottom:24px;display:grid}.paui-turn{gap:16px;min-width:0;display:grid}.paui-message{flex-direction:column;min-width:0;display:flex}.paui-message[data-role=user]{align-items:flex-end;gap:6px}.paui-message__bubble{min-width:0}.paui-message[data-role=user] .paui-message__bubble{background:var(--paui-user-bubble);border-radius:22px;max-width:min(525px,82%);padding:10px 16px}.paui-message[data-role=user][data-pending=true]{opacity:.68}.paui-message__label{display:none}.paui-message__content>:first-child,.paui-markdown>:first-child{margin-top:0}.paui-message__content>:last-child,.paui-markdown>:last-child{margin-bottom:0}.paui-markdown{overflow-wrap:anywhere;min-width:0;font-size:16px;line-height:28px}.paui-message[data-role=user] .paui-markdown{font-size:16px;line-height:24px}.paui-message__actions{align-items:center;gap:10px;height:28px;display:flex}.paui-message[data-role=assistant] .paui-message__actions{margin-top:16px;margin-left:-6px}.paui-message__action{width:28px;height:28px;color:var(--paui-text-muted);background:0 0;border:0;border-radius:50%;place-items:center;padding:6px;display:inline-grid}.pretty-aui .paui-message__action svg{width:16px;height:16px}.paui-message__action:hover{color:var(--paui-text);background:var(--paui-surface)}.paui-message__time{color:var(--paui-text-muted);opacity:0;white-space:nowrap;font-size:14px;line-height:24px;transition:opacity 80ms}.paui-message__time--start{padding-right:12px}.paui-message__time--end{padding-left:12px}.pretty-aui [data-time-hover-root]:hover .paui-message__time,.pretty-aui [data-time-hover-root]:focus-within .paui-message__time{opacity:1}.paui-markdown :is(p,ul,ol,pre,blockquote){margin:.72em 0}.paui-markdown :is(h1,h2,h3,h4){letter-spacing:-.015em;margin:1.15em 0 .45em;font-size:1em;font-weight:650}.paui-markdown :is(code),.paui-url,.paui-terminal pre,.paui-diff pre,.paui-resource pre{font-family:var(--paui-mono);font-size:.84em}.paui-markdown :not(pre)>code{background:var(--paui-surface);border-radius:5px;padding:.14em .35em}.paui-markdown pre,.paui-terminal pre,.paui-diff pre,.paui-resource pre{border:1px solid var(--paui-border);background:var(--paui-surface);white-space:pre;border-radius:9px;max-width:100%;padding:12px 14px;line-height:1.55;overflow:auto}.paui-markdown a,.paui-resource{color:var(--paui-accent);-webkit-text-decoration-color:color-mix(in srgb, var(--paui-accent) 45%, transparent);text-decoration-color:color-mix(in srgb, var(--paui-accent) 45%, transparent);text-underline-offset:3px}.paui-activities{gap:16px;min-width:0;display:grid}.paui-notice-group{gap:6px;min-width:0;display:grid}.paui-activity{min-width:0}.paui-host-notice{min-width:0;color:var(--paui-text-muted);overflow-wrap:anywhere;align-items:flex-start;gap:7px;padding:2px 0;font-size:13px;line-height:20px;display:flex}.paui-activity[data-kind=notice][data-level=error] .paui-host-notice{color:var(--paui-danger)}.paui-host-notice__icon{flex:none;place-items:center;width:16px;height:20px;display:inline-grid}.paui-host-notice__icon svg{width:14px;height:14px}.paui-thought,.paui-disclosure,.paui-diff,.paui-resource{min-width:0}.paui-thought>summary,.paui-disclosure>summary,.paui-diff>summary,.paui-resource>summary{min-height:28px;color:var(--paui-text-muted);cursor:pointer;border-radius:6px;align-items:center;gap:7px;font-size:13px;line-height:20px;list-style:none;display:flex}.paui-thought>summary:hover,.paui-disclosure>summary:hover{color:color-mix(in srgb, var(--paui-text) 78%, var(--paui-text-muted))}.pretty-aui summary::-webkit-details-marker{display:none}.paui-thought>summary svg,.paui-disclosure>summary svg,.paui-diff>summary svg,.paui-resource>summary svg{width:15px;height:15px}.paui-thought__body,.paui-disclosure__body{color:var(--paui-text-muted);padding:4px 0 4px 22px;font-size:14px;line-height:24px}.pretty-aui .paui-flow-summary{align-items:center;gap:0;min-width:0;height:24px;min-height:24px;line-height:24px;display:flex;position:relative;overflow:hidden}.paui-flow-leading{width:16px;height:16px;color:var(--paui-flow-copy);flex:none;justify-content:center;align-items:center;margin-right:6px;display:inline-flex;position:relative}.paui-flow-icon,.paui-flow-chevron{justify-content:center;align-items:center;transition:opacity .1s;display:inline-flex}.paui-flow-chevron{opacity:0;position:absolute;inset:0}.pretty-aui .paui-flow-leading svg{width:14px;height:14px}.pretty-aui .paui-flow-leading .paui-think-icon{fill:currentColor;stroke:none}.paui-flow-summary:hover .paui-flow-icon,.paui-thought[open] .paui-flow-icon,.paui-tool[open] .paui-flow-icon,.paui-context-injection[open] .paui-flow-icon{opacity:0}.paui-flow-summary:hover .paui-flow-chevron,.paui-thought[open] .paui-flow-chevron,.paui-tool[open] .paui-flow-chevron,.paui-context-injection[open] .paui-flow-chevron{opacity:1}.paui-flow-title{color:var(--paui-flow-title);flex:none;font-size:14px;font-weight:400;line-height:24px}.paui-flow-separator{background:var(--paui-flow-caption);border-radius:1px;flex:none;width:2px;height:2px;margin:0 8px}.paui-flow-preview{min-width:0;color:var(--paui-flow-copy);text-overflow:ellipsis;white-space:nowrap;flex:auto;font-size:14px;line-height:24px;overflow:hidden}.paui-flow-preview[data-follow-end=true]{text-overflow:clip}.paui-context-injection__body{box-sizing:border-box;width:calc(100% - 22px);max-height:141px;color:var(--paui-text-muted);background:var(--paui-surface);font:400 11px/16px var(--paui-mono);scrollbar-color:var(--paui-border) transparent;border-radius:8px;margin:4px 0 0 22px;padding:10px 12px 12px;overflow:auto}.paui-context-injection__body>*+*{margin-top:8px}.paui-context-block{gap:4px;min-width:0;display:grid}.paui-context-meta{min-width:0;color:var(--paui-text-muted);overflow-wrap:anywhere;flex-wrap:wrap;gap:4px 10px;display:flex}.paui-context-meta>span+span{color:var(--paui-flow-caption)}.paui-context-text{color:var(--paui-flow-copy);font:inherit;overflow-wrap:anywhere;white-space:pre-wrap;margin:0}.paui-context-identifier,.paui-context-truncated{color:var(--paui-flow-caption);overflow-wrap:anywhere}.paui-subagent-row{align-items:flex-start;gap:4px;width:100%;min-width:0;min-height:24px;display:flex}.paui-subagent{flex:auto;min-width:0}.paui-subagent-status{color:var(--paui-flow-caption);white-space:nowrap;flex:none;align-items:center;gap:8px;margin-left:12px;font-size:11px;line-height:24px;display:inline-flex}.paui-subagent-status__ongoing{align-items:center;gap:5px;display:inline-flex}.paui-subagent-status__spinner,.paui-session__spinner{border:1.5px solid color-mix(in srgb, var(--paui-accent) 28%, transparent);border-top-color:var(--paui-accent);border-radius:50%;width:9px;height:9px;animation:.8s linear infinite paui-subagent-spin}.paui-subagent-status[data-status=failed],.paui-subagent-status[data-status=cancelled],.paui-subagent:is([data-state=failed],[data-state=cancelled]) .paui-flow-leading{color:var(--paui-danger)}.paui-subagent-open{width:24px;height:24px;color:var(--paui-flow-copy);background:0 0;border:0;border-radius:6px;flex:none;place-items:center;padding:0;display:inline-grid}.paui-subagent-open:hover:not(:disabled){color:var(--paui-text);background:var(--paui-surface)}.paui-subagent-open svg{width:14px;height:14px}.paui-subagent[open] .paui-flow-icon{opacity:0}.paui-subagent[open] .paui-flow-chevron{opacity:1}@keyframes paui-subagent-spin{to{transform:rotate(360deg)}}.paui-thought[open] .paui-flow-separator,.paui-thought[open] .paui-flow-preview{display:none}.paui-tool[data-state=failed] .paui-flow-leading{color:var(--paui-danger)}.paui-thought[data-running=true]>.paui-flow-summary:after,.paui-tool:is([data-state=pending],[data-state=in_progress])>.paui-flow-summary:after{inset-block:0;background:linear-gradient(90deg, transparent 0%, color-mix(in srgb, var(--paui-background) 60%, transparent) 55%, transparent 100%);content:\"\";pointer-events:none;width:300px;animation:2.6s ease-out infinite paui-flow-sweep;position:absolute;left:0}@keyframes paui-flow-sweep{0%{left:-300px}90%,to{left:100%}}@media (prefers-reduced-motion:reduce){.paui-thought[data-running=true]>.paui-flow-summary:after,.paui-tool:is([data-state=pending],[data-state=in_progress])>.paui-flow-summary:after{animation:none}.paui-subagent-status__spinner,.paui-session__spinner{border-color:var(--paui-accent);background:var(--paui-accent);animation:none}}.paui-status{color:var(--paui-text-muted);font-family:var(--paui-mono);letter-spacing:.04em;text-transform:uppercase;margin-left:auto;font-size:9px}.paui-status:is([data-status=failed],[data-status=cancelled]){color:var(--paui-danger)}.paui-plan__list{gap:6px;margin:4px 0 0;padding:4px 0 4px 22px;list-style:none;display:grid}.paui-plan__list li{color:var(--paui-text-muted);grid-template-columns:12px 1fr;align-items:start;gap:8px;font-size:13px;line-height:20px;display:grid}.paui-plan__mark{border:1px solid;border-radius:50%;width:7px;height:7px;margin-top:6px}.paui-plan__list li[data-status=completed] .paui-plan__mark{border-color:var(--paui-success);background:var(--paui-success)}.paui-plan__list li[data-status=in_progress]{color:var(--paui-text)}.paui-plan__list li[data-status=in_progress] .paui-plan__mark{border-color:var(--paui-accent);background:var(--paui-accent);box-shadow:inset 0 0 0 2px var(--paui-background)}.paui-media{border-radius:10px;max-width:100%;max-height:420px;margin:10px 0;display:block}.paui-resource{align-items:center;gap:6px;display:inline-flex}.paui-resource svg{width:15px;height:15px}.paui-unsupported,.paui-muted{color:var(--paui-text-muted);font-size:12px}.paui-notice{background:var(--paui-accent-soft);border-radius:9px;align-items:center;gap:10px;padding:10px 12px;display:flex}.paui-notice>div,.paui-error>div{flex:1;min-width:0;display:grid}.paui-notice strong,.paui-error strong{font-size:12px}.paui-notice span,.paui-error span{color:var(--paui-text-muted);font-size:11px}.paui-notice svg,.paui-error svg{width:16px}.paui-empty{max-width:340px;color:var(--paui-text-muted);text-align:center;justify-items:center;margin:clamp(42px,12vh,90px) auto;display:grid}.paui-empty svg{width:24px;height:24px;color:var(--paui-accent);margin-bottom:12px}.paui-empty strong{color:var(--paui-text);letter-spacing:-.01em;font-size:16px;font-weight:600}.paui-empty p{margin:5px 0 0;font-size:12px}.paui-interactions{z-index:3;min-width:0;padding:0 var(--paui-gutter);background:var(--paui-background);gap:8px;display:grid}.paui-interactions:empty{display:none}.paui-error,.paui-interaction,.paui-auth{width:100%;max-width:var(--paui-content-width);border:1px solid var(--paui-border);background:var(--paui-surface);border-radius:12px;gap:11px;margin:0 auto;display:flex}.paui-error{border-color:color-mix(in srgb, var(--paui-danger) 30%, var(--paui-border));align-items:center;padding:10px 12px}.paui-error button,.paui-auth button,.paui-load-more{border:1px solid var(--paui-border);background:var(--paui-background);border-radius:8px;padding:6px 10px;font-size:12px}.paui-interaction{padding:14px}.paui-interaction__icon{width:28px;height:28px;color:var(--paui-accent);background:var(--paui-accent-soft);border-radius:8px;flex:none;place-items:center;display:grid}.paui-interaction__icon svg{width:16px}.paui-interaction__content{flex:1;gap:8px;min-width:0;display:grid}.paui-interaction__content>strong{font-size:13px}.paui-interaction__content>p{color:var(--paui-text-muted);margin:-3px 0 0;font-size:12px}.paui-interaction__actions{flex-wrap:wrap;gap:6px}.paui-button-primary,.paui-button-secondary,.paui-button-ghost{border-radius:8px;min-height:30px;padding:5px 10px;font-size:12px}.paui-button-primary{border:1px solid var(--paui-accent);color:var(--paui-on-accent);background:var(--paui-accent)}.paui-button-secondary{border:1px solid var(--paui-border);background:var(--paui-background)}.paui-button-ghost{color:var(--paui-text-muted);background:0 0;border:1px solid #0000}.paui-url{border:1px solid var(--paui-border);background:var(--paui-background);text-overflow:ellipsis;white-space:nowrap;border-radius:7px;padding:7px 8px;overflow:hidden}.paui-fields{gap:10px;display:grid}.paui-field{color:var(--paui-text-muted);gap:4px;font-size:11px;display:grid}.paui-field input,.paui-field select{border:1px solid var(--paui-border);min-height:34px;color:var(--paui-text);background:var(--paui-background);border-radius:7px;padding:6px 8px}.paui-field small{font-size:10px}.paui-field--check{align-items:center;display:flex}.paui-auth{justify-items:start;padding:16px;display:grid}.paui-auth>div{gap:6px;display:flex}.paui-auth>svg{color:var(--paui-accent)}.paui-composer-wrap{z-index:3;width:100%;padding:36px var(--paui-gutter) 8px;background:linear-gradient(to bottom, color-mix(in srgb, var(--paui-background) 0%, transparent) 0, var(--paui-background) 36px);justify-items:center;gap:6px;display:grid}.paui-composer-wrap[data-placement=hero]{transition:top .18s,transform .18s;position:absolute;top:50%;left:0;transform:translateY(-10%)}.paui-composer{width:100%;max-width:var(--paui-composer-width);background:var(--paui-surface-raised);box-shadow:var(--paui-shadow-raised);border:0;border-radius:22px;flex-direction:column;gap:12px;padding:10px 8px 6px 16px;font-size:16px;line-height:24px;transition:box-shadow .12s;display:flex;position:relative}.paui-composer__context{scrollbar-width:thin;flex-wrap:wrap;align-items:center;gap:6px;min-width:0;max-height:68px;padding-right:4px;display:flex;overflow-y:auto}.pretty-aui .paui-context-add{width:22px;height:22px;color:var(--paui-text-muted);background:0 0;border:0;border-radius:6px;flex:0 0 22px;place-items:center;padding:0;font-size:17px;line-height:1;display:inline-grid}.pretty-aui .paui-context-add:hover:not(:disabled){color:var(--paui-text);background:var(--paui-surface)}.paui-context-chip{border:1px solid var(--paui-border);min-width:0;max-width:min(260px,100% - 28px);color:var(--paui-text);background:var(--paui-background);border-radius:7px;align-items:center;gap:4px;padding:2px 3px 2px 8px;font-size:11px;line-height:18px;display:inline-flex}.paui-context-chip__label{text-overflow:ellipsis;white-space:nowrap;overflow:hidden}.pretty-aui .paui-context-chip button{width:18px;height:18px;color:var(--paui-text-muted);background:0 0;border:0;border-radius:5px;flex:0 0 18px;place-items:center;padding:0;font-size:14px;line-height:1;display:inline-grid}.pretty-aui .paui-context-chip button:hover:not(:disabled){color:var(--paui-text);background:var(--paui-surface)}.paui-composer textarea{resize:none;background:0 0;border:0;outline:0;width:100%;min-height:24px;max-height:336px;padding:2px 0;line-height:24px;overflow-y:auto}.pretty-aui .paui-composer textarea:focus-visible{outline:0}.paui-composer-wrap[data-placement=hero] .paui-composer textarea{min-height:52px}.paui-composer textarea::placeholder{color:var(--paui-text-muted)}.paui-composer__actions{justify-content:space-between;align-items:center;width:100%;min-width:0;display:flex}.pretty-aui .paui-send{color:var(--paui-on-accent);background:var(--paui-accent);border-radius:999px;transition:background-color .1s;transform:translateY(-2px)}.pretty-aui .paui-send:hover:not(:disabled){background:var(--paui-action-hover)}.pretty-aui .paui-send:disabled{opacity:.4}.pretty-aui .paui-send svg{stroke:none;width:16px;height:16px}.pretty-aui .paui-stop{color:#fff;background:var(--paui-accent)}.paui-config{width:auto;min-height:20px;color:var(--paui-text-muted);gap:8px;font-size:10px}.paui-config label{align-items:center;gap:4px;display:inline-flex}.paui-config__field{min-width:0;position:relative}.pretty-aui .paui-config__trigger{max-width:min(220px,45cqw);min-height:20px;color:var(--paui-text-muted);background:0 0;border:0;border-radius:6px;outline:0;align-items:center;gap:3px;padding:1px 4px;font-size:10px;line-height:16px;text-decoration:none;display:inline-flex}.paui-config__trigger>span{text-overflow:ellipsis;white-space:nowrap;min-width:0;overflow:hidden}.pretty-aui .paui-config__trigger>svg{width:12px;height:12px;color:var(--paui-text-muted);transition:transform .12s}.pretty-aui .paui-config__trigger[aria-expanded=true]>svg{transform:rotate(180deg)}.pretty-aui .paui-config__trigger:hover:not(:disabled),.pretty-aui .paui-config__trigger:focus-visible,.pretty-aui .paui-config__trigger[aria-expanded=true]{color:var(--paui-text-muted);background:var(--paui-surface);outline:0;text-decoration:none}.paui-config__listbox{--paui-config-scrollbar:color-mix(in srgb, var(--paui-text-muted) 34%, transparent);--paui-config-scrollbar-hover:color-mix(in srgb, var(--paui-text-muted) 56%, transparent);z-index:20;overscroll-behavior:contain;width:max-content;min-width:min(220px,100cqw - 32px);max-width:min(360px,100cqw - 32px);max-height:min(320px,100vh - 96px);color:var(--paui-text);background:var(--paui-surface-raised);box-shadow:0 16px 40px #0000001f, var(--paui-shadow-raised);border:0;border-radius:12px;padding:4px;font-size:12px;line-height:20px;position:absolute;bottom:calc(100% + 8px);left:0;overflow:hidden auto}@supports not selector(::-webkit-scrollbar){.paui-config__listbox{scrollbar-width:thin;scrollbar-color:var(--paui-config-scrollbar) transparent}}.paui-config__listbox::-webkit-scrollbar{width:8px;height:8px}.paui-config__listbox::-webkit-scrollbar-track{background:0 0}.paui-config__listbox::-webkit-scrollbar-corner{background:0 0}.paui-config__listbox::-webkit-scrollbar-thumb{background:var(--paui-config-scrollbar);background-clip:padding-box;border:2px solid #0000;border-radius:999px}.paui-config__listbox::-webkit-scrollbar-thumb:hover{background:var(--paui-config-scrollbar-hover);background-clip:padding-box}.pretty-aui .paui-config__option{width:100%;min-height:32px;color:var(--paui-text);text-align:left;background:0 0;border:0;border-radius:8px;outline:0;align-items:center;gap:8px;padding:6px 8px;display:flex}.paui-config__option>span:first-child{text-overflow:ellipsis;white-space:nowrap;flex:auto;min-width:0;overflow:hidden}.pretty-aui .paui-config__option[data-active=true],.pretty-aui .paui-config__option:focus-visible{background:var(--paui-surface);outline:0}.paui-config__check{width:16px;height:16px;color:var(--paui-text);flex:0 0 16px;place-items:center;display:inline-grid}.pretty-aui .paui-config__check svg{width:14px;height:14px}.paui-commands{right:var(--paui-gutter);bottom:76px;left:var(--paui-gutter);max-width:var(--paui-composer-width);border:1px solid var(--paui-border);background:var(--paui-surface-raised);box-shadow:var(--paui-shadow-raised);border-radius:12px;margin:0 auto;display:grid;position:absolute;overflow:hidden}.paui-commands button{border:0;border-bottom:1px solid var(--paui-border);text-align:left;background:0 0;grid-template-columns:minmax(110px,auto) 1fr;gap:10px;padding:8px 10px;display:grid}.paui-commands button:hover{background:var(--paui-surface)}.paui-commands code{color:var(--paui-accent);font-family:var(--paui-mono);font-size:11px}.paui-commands span{color:var(--paui-text-muted);font-size:11px}.paui-to-bottom{border:1px solid var(--paui-border);background:var(--paui-surface-raised);box-shadow:var(--paui-shadow-raised);border-radius:50%}.paui-to-bottom-row{flex:none;place-items:center;height:46px;display:grid}.paui-drawer-backdrop{z-index:20;background:0 0;justify-content:flex-end;display:flex;position:absolute;inset:0}.paui-drawer{border-left:1px solid var(--paui-border);background:var(--paui-background);width:min(340px,88%);height:100%;min-height:0;box-shadow:var(--paui-shadow-raised);grid-template-rows:auto minmax(0,1fr);display:grid;position:relative}.paui-drawer>header{border-bottom:1px solid var(--paui-border);justify-content:space-between;align-items:center;min-height:56px;padding:10px 12px 10px 16px;display:flex}.paui-session-list{overscroll-behavior:contain;scrollbar-color:var(--paui-border) transparent;scrollbar-gutter:stable;align-content:start;gap:2px;min-height:0;padding:8px;display:grid;overflow-y:auto}.paui-session{box-sizing:border-box;border-radius:8px;grid-template-columns:minmax(0,1fr) auto;align-items:center;height:32px;padding:0 4px 0 8px;transition:background-color .1s;display:grid}.paui-session:is(:hover,:focus-within,[data-active=true],[data-menu-open=true]){background:var(--paui-surface)}.paui-session__select{min-width:0;height:100%;color:var(--paui-text);text-align:left;background:0 0;border:0;align-items:center;gap:4px;padding:0;display:flex}.pretty-aui .paui-session__select:disabled{cursor:default;opacity:1}.paui-session__title{text-overflow:ellipsis;white-space:nowrap;min-width:0;font-size:14px;font-weight:400;line-height:20px;overflow:hidden}.paui-session__spinner{flex:none}.paui-session__trailing{place-items:center end;min-width:32px;max-width:152px;display:grid;overflow:hidden}.paui-session__trailing>*{grid-area:1/1}.paui-session__meta{pointer-events:none;min-width:0;color:var(--paui-text-muted);text-overflow:ellipsis;white-space:nowrap;align-items:center;font-size:12px;line-height:20px;transition:opacity .1s;display:flex;overflow:hidden}.paui-session__meta>span:not(.paui-session__meta-separator){text-overflow:ellipsis;min-width:0;overflow:hidden}.paui-session__meta-separator{flex:none;margin:0 5px}.paui-session__action{width:32px;height:32px;color:var(--paui-text-muted);opacity:0;pointer-events:none;background:0 0;border:0;place-items:center;padding:0;transition:color .1s,opacity .1s;display:inline-grid}.paui-session__action svg{width:16px;height:16px}.paui-session__action:hover:not(:disabled){color:var(--paui-text)}.paui-session[data-has-actions=true]:is(:hover,:focus-within,[data-menu-open=true]) .paui-session__meta{opacity:0}.paui-session[data-has-actions=true]:is(:hover,:focus-within,[data-menu-open=true]) .paui-session__action{opacity:1;pointer-events:auto}.paui-session-menu{z-index:2;box-sizing:border-box;border:1px solid var(--paui-border);background:var(--paui-surface-raised);width:min(164px,100% - 16px);box-shadow:var(--paui-shadow-raised);border-radius:12px;padding:4px;display:grid;position:absolute}.paui-session-menu>button{width:100%;min-height:34px;color:var(--paui-danger);text-align:left;background:0 0;border:0;border-radius:8px;align-items:center;gap:8px;padding:6px 8px;font-size:13px;line-height:20px;display:flex}.paui-session-menu>button span{text-overflow:ellipsis;white-space:nowrap;min-width:0;overflow:hidden}.paui-session-menu>button:hover:not([aria-disabled=true]){background:color-mix(in srgb, var(--paui-danger) 10%, transparent)}.paui-session-menu>button[aria-disabled=true]{cursor:not-allowed;opacity:.46}.paui-session-menu svg{width:16px;height:16px}@media (hover:none){.paui-session[data-has-actions=true] .paui-session__meta{opacity:0}.paui-session[data-has-actions=true] .paui-session__action{opacity:1;pointer-events:auto}}@media (prefers-reduced-motion:reduce){.paui-session,.paui-session__action,.paui-session__meta{transition:none}}.paui-usage{max-width:156px;color:var(--paui-text-muted);font-family:var(--paui-mono);text-overflow:ellipsis;white-space:nowrap;font-size:10px;overflow:hidden}.paui-tool-block{box-sizing:border-box;border:1px solid var(--paui-border);width:100%;min-width:0;color:var(--paui-text);background:color-mix(in srgb, var(--paui-surface) 72%, transparent);font:400 12px/20px var(--paui-mono);border-radius:12px;overflow:hidden}.paui-tool-block__banner,.paui-tool-terminal__header,.paui-tool-io__section-header{justify-content:space-between;align-items:flex-start;gap:12px;min-width:0;display:flex}.paui-tool-block__banner{border-bottom:1px solid var(--paui-border);background:color-mix(in srgb, var(--paui-surface-raised) 36%, transparent);padding:9px 14px}.paui-tool-block__label{text-overflow:ellipsis;white-space:nowrap;min-width:0;overflow:hidden}.paui-tool-block__copy,.paui-tool-block__fold{color:var(--paui-text-muted);font:500 12px/20px var(--paui-sans);background:0 0;border:0;padding:0}.paui-tool-block__copy{flex:none}.paui-tool-block__copy:hover,.paui-tool-block__fold:hover{color:var(--paui-text)}.paui-tool-block__fold{border-block:1px solid var(--paui-border);text-align:left;width:100%;padding:5px 14px;display:block}.paui-tool-block__empty{color:var(--paui-text-muted);padding:12px 14px}.paui-tool-terminal__header{scrollbar-color:var(--paui-border) transparent;max-height:152px;padding:9px 14px 9px 30px;overflow:auto}.paui-tool-terminal:not([data-state=running]) .paui-tool-terminal__header{border-bottom:1px solid var(--paui-border)}.paui-tool-terminal__prompt{flex:1;min-width:max-content}.paui-tool-terminal__prompt-line{white-space:pre;align-items:baseline;gap:9px;min-width:0;display:flex;position:relative}.paui-tool-terminal__state{background:var(--paui-success);border-radius:50%;width:7px;height:7px;position:absolute;top:7px;left:-18px}.paui-tool-terminal[data-state=running] .paui-tool-terminal__state{background:var(--paui-accent);box-shadow:0 0 0 3px var(--paui-accent-soft);animation:1.5s ease-in-out infinite paui-pulse}@keyframes paui-pulse{50%{opacity:.48}}.paui-tool-terminal[data-state=failed] .paui-tool-terminal__state{background:var(--paui-danger)}.paui-tool-terminal__cwd{color:var(--paui-text-muted);flex:none}.paui-tool-terminal__command,.paui-tool-read__content,.paui-tool-diff__line{white-space:pre}.paui-tool-terminal__output{box-sizing:border-box;width:100%;max-height:224px;color:var(--paui-text);font:inherit;scrollbar-color:var(--paui-border) transparent;white-space:pre;background:0 0;margin:0;padding:12px 14px 12px 30px;overflow:auto}.paui-tool-terminal[data-state=failed] .paui-tool-terminal__output{color:var(--paui-danger)}.paui-tool-read__body,.paui-tool-diff__body{scrollbar-color:var(--paui-border) transparent;max-height:286px;overflow:auto}.paui-tool-read__line{grid-template-columns:minmax(38px,max-content) max-content;width:max-content;min-width:100%;display:grid}.paui-tool-read__gutter{color:var(--paui-text-muted);text-align:right;-webkit-user-select:none;user-select:none;padding:0 12px 0 8px}.paui-tool-read__content{padding-right:16px}.paui-tool-diff__line{box-sizing:border-box;width:max-content;min-width:100%;padding:0 14px}.paui-tool-diff__line[data-line-kind=add]{color:color-mix(in srgb, var(--paui-success) 88%, var(--paui-text));background:color-mix(in srgb, var(--paui-success) 11%, transparent)}.paui-tool-diff__line[data-line-kind=delete]{color:color-mix(in srgb, var(--paui-danger) 88%, var(--paui-text));background:color-mix(in srgb, var(--paui-danger) 10%, transparent)}.paui-tool-diff__line[data-line-kind=meta]{color:var(--paui-text-muted)}.paui-tool-diff__footer{border-top:1px solid var(--paui-border);color:var(--paui-text-muted);padding:6px 14px;font-size:11px}.paui-tool-io__section{scrollbar-color:var(--paui-border) transparent;max-height:190px;overflow:auto}.paui-tool-io__section-header{z-index:1;color:var(--paui-text-muted);background:var(--paui-surface);font:600 10px/18px var(--paui-sans);letter-spacing:.06em;text-transform:uppercase;padding:7px 14px;position:sticky;top:0}.paui-tool-io__section[data-error=true] .paui-tool-io__section-header,.paui-tool-io__section[data-error=true] .paui-tool-io__content{color:var(--paui-danger)}.paui-tool-io__content{min-width:max-content;padding:8px 14px 12px}.paui-tool-io__content pre{color:inherit;font:inherit;white-space:pre;margin:0}.paui-tool-io__divider{border-top:1px solid var(--paui-border);display:block}.paui-tool-supplementary{margin-top:8px}@media (prefers-reduced-motion:reduce){.paui-tool-terminal[data-state=running] .paui-tool-terminal__state{animation:none}}.paui-load-more{margin-top:6px}.paui-error-text{color:var(--paui-danger);padding:8px;font-size:11px}.paui-sr-only{clip:rect(0, 0, 0, 0);white-space:nowrap;border:0;width:1px;height:1px;padding:0;position:absolute;overflow:hidden}@container pretty-aui (width<=560px){.paui-header{min-height:48px;padding:7px 8px 7px 12px}.paui-identity--child{gap:4px}.paui-identity--child .paui-presence,.paui-lineage__ancestor{display:none}.paui-lineage{align-items:center;display:flex}.paui-lineage__back{display:inline-grid}.paui-lineage__titles{flex:auto;min-width:0}.paui-body{padding-top:18px}.paui-transcript{padding-bottom:18px}.paui-message[data-role=user] .paui-message__bubble{max-width:88%}.paui-markdown{font-size:15px;line-height:25px}.paui-message[data-role=user] .paui-markdown{font-size:15px;line-height:23px}.paui-interaction__actions{align-items:stretch}.paui-button-primary,.paui-button-secondary,.paui-button-ghost{flex:auto}.paui-composer-wrap{padding-left:10px;padding-right:10px}.paui-composer{padding-left:14px}}.pretty-aui[data-surface=sidebar] .paui-identity--child{gap:4px}.pretty-aui[data-surface=sidebar] :is(.paui-identity--child .paui-presence,.paui-lineage__ancestor){display:none}.pretty-aui[data-surface=sidebar] .paui-lineage{align-items:center;display:flex}.pretty-aui[data-surface=sidebar] .paui-lineage__back{display:inline-grid}@container pretty-aui (width<=380px){.paui-identity{gap:7px}.paui-protocol{display:none}.paui-message[data-role=user] .paui-message__bubble{max-width:92%}.paui-interaction{padding:11px}.paui-interaction__icon{display:none}}@media (prefers-reduced-motion:reduce){.pretty-aui *,.pretty-aui :before,.pretty-aui :after{scroll-behavior:auto!important;transition-duration:.01ms!important;animation-duration:.01ms!important;animation-iteration-count:1!important}}", yc = "Acp-Connection-Id", bc = "Acp-Session-Id", xc = "text/event-stream", Sc = "application/json";
i.session_cancel, i.session_close, i.session_delete, i.session_fork, i.session_load, i.session_prompt, i.session_resume, i.session_set_config_option, i.session_set_mode, i.nes_suggest, i.nes_accept, i.nes_reject, i.nes_close, i.document_did_open, i.document_did_change, i.document_did_close, i.document_did_save, i.document_did_focus;
function Cc(e) {
	if (!r(e)) return;
	let t = e.sessionId;
	return typeof t == "string" ? t : void 0;
}
function wc(e) {
	return "method" in e ? Cc(e.params) : void 0;
}
function Tc(t) {
	if (!e(t) || !("result" in t) || !r(t.result)) return;
	let n = t.result.sessionId;
	return typeof n == "string" ? n : void 0;
}
function Ec(e) {
	return e.jsonrpc === "2.0" && "id" in e && "method" in e && e.method === i.initialize;
}
function Dc(e) {
	if (typeof e == "string") return `string:${e}`;
	if (typeof e == "number") return `number:${e}`;
	if (e === null) return "null";
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/cookie-store.js
var Oc = class {
	cookies = /* @__PURE__ */ new Map();
	store(e) {
		for (let t of kc(e)) {
			let e = jc(t);
			e && this.cookies.set(e.name, e.value);
		}
	}
	apply(e) {
		let t = Mc(this.cookieHeader(), e.get("Cookie"));
		t && e.set("Cookie", t);
	}
	clear() {
		this.cookies.clear();
	}
	cookieHeader() {
		return this.cookies.size === 0 ? void 0 : Array.from(this.cookies).map(([e, t]) => `${e}=${t}`).join("; ");
	}
};
function kc(e) {
	let t = e.getSetCookie;
	if (typeof t == "function") return t.call(e).flatMap(Ac);
	let n = e.get("Set-Cookie");
	return n ? Ac(n) : [];
}
function Ac(e) {
	return e.split(/,(?=\s*[^;,\s]+=)/).map((e) => e.trim()).filter((e) => e.length > 0);
}
function jc(e) {
	let t = e.split(";", 1)[0], n = t.indexOf("=");
	if (n <= 0) return;
	let r = t.slice(0, n).trim();
	if (r) return {
		name: r,
		value: t.slice(n + 1).trim()
	};
}
function Mc(e, t) {
	let n = /* @__PURE__ */ new Map();
	for (let t of Nc(e)) n.set(t.name, t.value);
	for (let e of Nc(t ?? void 0)) n.set(e.name, e.value);
	return n.size === 0 ? void 0 : Array.from(n).map(([e, t]) => `${e}=${t}`).join("; ");
}
function Nc(e) {
	return e ? e.split(";").map(Pc).filter((e) => e !== void 0) : [];
}
function Pc(e) {
	let t = e.indexOf("=");
	if (t <= 0) return;
	let n = e.slice(0, t).trim();
	if (n) return {
		name: n,
		value: e.slice(t + 1).trim()
	};
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/sse.js
async function* Fc(e) {
	let t = new TextDecoder(), n = e.getReader(), r = new Vt(), i = [], a = (e) => {
		let n = t.decode(e);
		return n.endsWith("\r") ? n.slice(0, -1) : n;
	}, o = () => {
		if (i.length === 0) return;
		let e = i;
		return i = [], Ic(e);
	};
	try {
		for (;;) {
			let e = await n.read();
			if (e.done) break;
			for (let t of r.push(e.value)) {
				let e = a(t);
				if (e === "") {
					let e = o();
					e && (yield e);
				} else i.push(e);
			}
		}
		let e = r.flush();
		if (e) {
			let t = a(e);
			t !== "" && i.push(t);
		}
		let t = o();
		t && (yield t);
	} finally {
		n.releaseLock();
	}
}
function Ic(e) {
	let t = e.filter((e) => e.startsWith("data:")).map((e) => {
		let t = e.slice(5);
		return t.startsWith(" ") ? t.slice(1) : t;
	});
	if (t.length === 0) return;
	let n = t.join("\n");
	if (n.trim()) try {
		let e = JSON.parse(n);
		if (r(e) || Array.isArray(e)) return e;
		console.warn("Skipping SSE payload that is not an object or array");
		return;
	} catch (e) {
		console.warn("Failed to parse SSE JSON payload:", e);
		return;
	}
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/http-stream.js
function Lc(e, t = {}) {
	return new Rc(e, t).stream;
}
var Rc = class {
	serverUrl;
	stream;
	fetchImpl;
	headers;
	cookiePolicy;
	cookieStore;
	ownsCookieStore;
	abortController = new AbortController();
	knownSessions = /* @__PURE__ */ new Set();
	sessionSseReady = /* @__PURE__ */ new Map();
	pendingResponseSessions = /* @__PURE__ */ new Map();
	pendingSessionRequests = /* @__PURE__ */ new Map();
	readableController;
	connectionId;
	isClosed = !1;
	writeChain = Promise.resolve();
	constructor(e, t) {
		this.serverUrl = e, this.fetchImpl = zc(t.fetch), this.headers = t.headers ?? {}, this.cookiePolicy = t.cookies ?? "include", this.cookieStore = t.cookieStore ?? new Oc(), this.ownsCookieStore = t.cookieStore === void 0, this.stream = {
			readable: new ReadableStream({
				start: (e) => {
					this.readableController = e;
				},
				cancel: () => this.close()
			}),
			writable: new WritableStream({
				write: (e) => (this.writeChain = this.writeChain.then(() => this.writeMessage(e)), this.writeChain),
				close: () => this.close(),
				abort: () => this.close()
			})
		};
	}
	async writeMessage(e) {
		if (this.isClosed) throw Error("ACP HTTP stream is closed");
		if (Array.isArray(e)) throw TypeError("ACP HTTP transport does not support JSON-RPC batch messages");
		if (!this.connectionId) {
			await this.postInitialize(e);
			return;
		}
		await this.postConnectedMessage(e);
	}
	async postInitialize(t) {
		let n;
		try {
			if (!Ec(t)) throw Error("ACP HTTP stream first message must be initialize");
			let r = await this.fetchRequest({
				method: "POST",
				headers: { "Content-Type": Sc },
				body: JSON.stringify(t),
				signal: this.abortController.signal
			});
			if (!r.ok) throw await Bc("ACP initialize failed", r);
			let i = r.headers.get(yc);
			if (!i) throw Error("ACP initialize response missing Acp-Connection-Id");
			n = i, this.throwIfClosedDuringInitialize();
			let a = await r.json();
			if (this.throwIfClosedDuringInitialize(), !e(a)) throw Error("ACP initialize response was not a JSON-RPC response");
			if (Dc(a.id) !== ("id" in t ? Dc(t.id) : void 0)) throw Error("ACP initialize response id did not match initialize request");
			this.connectionId = i, this.openConnectionSse(), this.enqueue(a);
		} catch (e) {
			throw this.isClosed && n ? (await this.deleteConnection(n).catch(() => void 0), this.clearOwnedCookieStore()) : this.errorReadable(e, n), e;
		}
	}
	throwIfClosedDuringInitialize() {
		if (this.isClosed) throw Error("ACP HTTP stream is closed");
	}
	async postConnectedMessage(e) {
		let t = this.connectionId;
		if (!t) throw Error("ACP HTTP stream is not initialized");
		let n = this.sessionIdForOutboundMessage(e);
		n && await this.openSessionSse(n);
		let r = n && "method" in e && "id" in e ? Dc(e.id) : void 0;
		n && r && this.pendingSessionRequests.set(r, n);
		try {
			let r = await this.fetchRequest({
				method: "POST",
				headers: {
					"Content-Type": Sc,
					[yc]: t,
					...n ? { [bc]: n } : {}
				},
				body: JSON.stringify(e),
				signal: this.abortController.signal
			});
			if (!r.ok) throw await Bc("ACP POST failed", r);
			if (!("method" in e) && "id" in e) {
				let t = Dc(e.id);
				t && this.pendingResponseSessions.delete(t);
			}
		} catch (e) {
			throw r && this.pendingSessionRequests.delete(r), this.errorReadable(e), e;
		}
	}
	sessionIdForOutboundMessage(e) {
		let t = wc(e);
		if (t) return t;
		if (!("id" in e) || "method" in e) return;
		let n = Dc(e.id);
		return n ? this.pendingResponseSessions.get(n) : void 0;
	}
	openConnectionSse() {
		let e = this.connectionId;
		e && this.openSse({ [yc]: e });
	}
	openSessionSse(e) {
		let t = this.sessionSseReady.get(e);
		if (t) return t;
		if (this.knownSessions.has(e)) return Promise.resolve();
		let n = this.connectionId;
		if (!n) return Promise.resolve();
		let r = !1, i = () => {}, a = () => {}, o = new Promise((e, t) => {
			i = e, a = t;
		}), s = (e) => {
			r || (r = !0, e());
		};
		return o.catch(() => void 0), this.knownSessions.add(e), this.sessionSseReady.set(e, o), this.openSse({
			[yc]: n,
			[bc]: e
		}, {
			onOpen: () => {
				s(i);
			},
			onError: (e) => {
				s(() => {
					a(e);
				});
			},
			onClose: () => {
				this.sessionSseReady.delete(e), s(() => {
					a(/* @__PURE__ */ Error("ACP session SSE stream closed before opening"));
				});
			}
		}), o;
	}
	async openSse(e, t = {}) {
		let n = e[bc];
		try {
			let r = await this.fetchRequest({
				method: "GET",
				headers: {
					Accept: xc,
					...e
				},
				signal: this.abortController.signal
			});
			if (!r.ok) throw await Bc("ACP SSE connection failed", r);
			if (!r.body) throw Error("ACP SSE response missing body");
			t.onOpen?.();
			for await (let t of Fc(r.body)) {
				if (this.isClosed) return;
				if (Array.isArray(t)) throw TypeError("ACP HTTP transport does not support JSON-RPC batch messages");
				let n = Tc(t);
				n && this.openSessionSse(n), this.trackServerRequestRoute(t, e[bc]), this.trackInboundResponse(t), this.enqueue(t);
			}
			this.handleSseEof(n);
		} catch (e) {
			if (this.isClosed || this.abortController.signal.aborted) return;
			t.onError?.(e), this.errorReadable(e);
		} finally {
			t.onClose?.();
		}
	}
	handleSseEof(e) {
		if (!(this.isClosed || this.abortController.signal.aborted)) {
			if (!e) {
				this.errorReadable(/* @__PURE__ */ Error("ACP connection SSE stream closed"));
				return;
			}
			this.knownSessions.delete(e), this.sessionSseReady.delete(e), this.hasPendingSessionRequest(e) && this.errorReadable(/* @__PURE__ */ Error("ACP session SSE stream closed"));
		}
	}
	trackServerRequestRoute(e, t) {
		if (!t || !("method" in e) || !("id" in e)) return;
		let n = Dc(e.id);
		n && this.pendingResponseSessions.set(n, t);
	}
	trackInboundResponse(t) {
		if (!e(t)) return;
		let n = Dc(t.id);
		n && this.pendingSessionRequests.delete(n);
	}
	hasPendingSessionRequest(e) {
		for (let t of this.pendingSessionRequests.values()) if (t === e) return !0;
		return !1;
	}
	async fetchRequest(e) {
		let t = await this.fetchImpl(this.serverUrl, {
			...e,
			credentials: this.cookiePolicy,
			headers: this.createRequestHeaders(e.headers)
		});
		return this.cookiePolicy === "include" && this.cookieStore.store(t.headers), t;
	}
	createRequestHeaders(e) {
		let t = new Headers(this.headers);
		return new Headers(e).forEach((e, n) => {
			t.set(n, e);
		}), this.cookiePolicy === "include" && this.cookieStore.apply(t), t;
	}
	async close() {
		if (!this.isClosed) {
			this.isClosed = !0, this.abortController.abort();
			try {
				await this.deleteConnection();
			} finally {
				this.clearOwnedCookieStore(), this.closeReadable();
			}
		}
	}
	async deleteConnection(e = this.connectionId) {
		if (!e) return;
		let t = await this.fetchRequest({
			method: "DELETE",
			headers: { [yc]: e }
		});
		if (!t.ok) throw await Bc("ACP DELETE failed", t);
	}
	clearOwnedCookieStore() {
		this.ownsCookieStore && this.cookieStore.clear();
	}
	enqueue(e) {
		try {
			this.readableController?.enqueue(e);
		} catch (e) {
			this.errorReadable(e);
		}
	}
	errorReadable(e, t = this.connectionId) {
		if (!this.isClosed) {
			this.isClosed = !0, this.abortController.abort(), this.deleteConnection(t).catch(() => void 0).finally(() => {
				this.clearOwnedCookieStore();
			});
			try {
				this.readableController?.error(e);
			} catch {}
		}
	}
	closeReadable() {
		try {
			this.readableController?.close();
		} catch {}
	}
};
function zc(e) {
	if (e) return e;
	if (typeof globalThis.fetch == "function") return (e, t) => globalThis.fetch(e, t);
	throw Error("createHttpStream requires globalThis.fetch or options.fetch");
}
async function Bc(e, t) {
	let n = await t.text().catch(() => "");
	return Error(n ? `${e}: ${t.status} ${t.statusText}: ${n}` : `${e}: ${t.status} ${t.statusText}`);
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/ws-utils.js
function Vc(e, t, n) {
	if (e.on) {
		let r = (...e) => {
			n(...Uc(t, e));
		};
		return e.on(t, r), () => {
			if (e.off) {
				e.off(t, r);
				return;
			}
			e.removeListener?.(t, r);
		};
	}
	if (e.addEventListener) {
		let r = (e) => n(e);
		return e.addEventListener(t, r), () => {
			e.removeEventListener?.(t, r);
		};
	}
	throw Error("WebSocket object does not support event listeners");
}
function Hc(e) {
	let t = Gc(e);
	if (typeof t == "string") return t;
}
function Uc(e, t) {
	return e !== "message" || typeof t[1] != "boolean" ? t : t[1] ? [void 0] : [Wc(t[0])];
}
function Wc(e) {
	if (typeof e == "string") return e;
	if (e instanceof ArrayBuffer || ArrayBuffer.isView(e)) return new TextDecoder().decode(e);
	if (qc(e)) return Jc(e);
}
function Gc(e) {
	let [t] = e;
	return Kc(t) ? t.data : t;
}
function Kc(e) {
	return typeof e == "object" && !!e && "data" in e;
}
function qc(e) {
	return Array.isArray(e) && e.every(ArrayBuffer.isView);
}
function Jc(e) {
	let t = e.reduce((e, t) => e + t.byteLength, 0), n = new Uint8Array(t), r = 0;
	for (let t of e) n.set(new Uint8Array(t.buffer, t.byteOffset, t.byteLength), r), r += t.byteLength;
	return new TextDecoder().decode(n);
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/ws-stream.js
var Yc = 1;
function Xc(e, t = {}) {
	return new Zc(e, t).stream;
}
var Zc = class {
	stream;
	socket;
	cookieStore;
	ownsCookieStore;
	readableController;
	isClosed = !1;
	openPromise;
	resolveOpen;
	rejectOpen;
	detachListeners = [];
	sendQueue = Promise.resolve();
	constructor(e, t) {
		let n = nl(t.WebSocket), r = t.cookies ?? "include";
		this.cookieStore = t.cookieStore ?? new Oc(), this.ownsCookieStore = t.cookieStore === void 0, this.socket = new n(e, t.protocols, { headers: Qc(t.headers, r, this.cookieStore) }), this.openPromise = new Promise((e, t) => {
			this.resolveOpen = e, this.rejectOpen = t;
		}), this.openPromise.catch(() => void 0), this.detachListeners.push(Vc(this.socket, "open", () => {
			this.resolveOpen?.(), this.resolveOpen = void 0, this.rejectOpen = void 0, this.openPromise = void 0;
		})), this.detachListeners.push(Vc(this.socket, "message", (...e) => {
			this.handleSocketMessage(e);
		})), this.detachListeners.push(Vc(this.socket, "close", () => {
			this.closeReadable();
		})), this.detachListeners.push(Vc(this.socket, "error", (e) => {
			this.errorReadable(e);
		})), r === "include" && this.detachListeners.push(Vc(this.socket, "upgrade", (e) => {
			let t = el(e);
			t && this.cookieStore.store(t);
		})), this.stream = {
			readable: new ReadableStream({
				start: (e) => {
					this.readableController = e;
				},
				cancel: () => {
					this.close();
				}
			}),
			writable: new WritableStream({
				write: (e) => this.queueMessage(e),
				close: () => {
					this.close();
				},
				abort: () => {
					this.close();
				}
			})
		};
	}
	queueMessage(e) {
		let t = this.sendQueue.then(() => this.sendMessage(e));
		return this.sendQueue = t.catch(() => {}), t;
	}
	async sendMessage(e) {
		if (this.isClosed || (await this.waitForOpen(), this.isClosed)) throw Error("ACP WebSocket stream is closed");
		this.socket.send(JSON.stringify(e));
	}
	async waitForOpen() {
		this.socket.readyState !== void 0 && this.socket.readyState !== Yc && await this.openPromise;
	}
	handleSocketMessage(e) {
		if (this.isClosed) return;
		let t = Hc(e);
		if (t === void 0) return;
		let n;
		try {
			n = JSON.parse(t);
		} catch {
			this.sendProtocolError(w.parseError());
			return;
		}
		if (!r(n) && !Array.isArray(n)) {
			this.sendProtocolError(w.invalidRequest(n));
			return;
		}
		this.readableController?.enqueue(n);
	}
	sendProtocolError(e) {
		this.queueMessage(C(e)).catch((e) => {
			this.errorReadable(e);
		});
	}
	close() {
		this.closeSocket(), this.closeReadable();
	}
	closeSocket() {
		try {
			this.socket.close();
		} catch (e) {
			console.warn("Failed to close ACP WebSocket:", e);
		}
	}
	clearOwnedCookieStore() {
		this.ownsCookieStore && this.cookieStore.clear();
	}
	closeReadable() {
		if (!this.isClosed) {
			this.isClosed = !0, this.clearOwnedCookieStore();
			for (let e of this.detachListeners.splice(0)) e();
			this.rejectOpen?.(/* @__PURE__ */ Error("ACP WebSocket stream closed before open")), this.rejectOpen = void 0, this.resolveOpen = void 0, this.openPromise = void 0;
			try {
				this.readableController?.close();
			} catch {}
		}
	}
	errorReadable(e) {
		if (!this.isClosed) {
			this.isClosed = !0, this.clearOwnedCookieStore();
			for (let e of this.detachListeners.splice(0)) e();
			this.rejectOpen?.(e), this.rejectOpen = void 0, this.resolveOpen = void 0, this.openPromise = void 0, this.readableController?.error(e);
		}
	}
};
function Qc(e, t, n) {
	let r = e ? { ...e } : {};
	if (t === "include") {
		let t = new Headers(e);
		n.apply(t);
		let i = t.get("Cookie");
		i && (r[$c(r, "Cookie") ?? "Cookie"] = i);
	}
	return Object.keys(r).length > 0 ? r : void 0;
}
function $c(e, t) {
	return Object.keys(e).find((e) => e.toLowerCase() === t.toLowerCase());
}
function el(e) {
	if (e instanceof Headers) return e;
	if (!(!r(e) || !("headers" in e))) return tl(e.headers);
}
function tl(e) {
	if (e instanceof Headers) return e;
	if (!r(e)) return;
	let t = new Headers();
	for (let [n, r] of Object.entries(e)) {
		if (Array.isArray(r)) {
			for (let e of r) t.append(n, String(e));
			continue;
		}
		r !== void 0 && t.set(n, String(r));
	}
	return t;
}
function nl(e) {
	if (e) return e;
	if (typeof globalThis.WebSocket == "function") return globalThis.WebSocket;
	throw Error("createWebSocketStream requires globalThis.WebSocket or options.WebSocket");
}
//#endregion
//#region src/core/transport.ts
function rl(e, t = {}) {
	let n = al(e, t.fetch ?? globalThis.fetch);
	return { open({ signal: r }) {
		return ol(Lc(e, {
			fetch: n,
			...t.headers ? { headers: { ...t.headers } } : {},
			...t.cookies ? { cookies: t.cookies } : {}
		}), r);
	} };
}
function il(e, t = {}) {
	return { open({ signal: n }) {
		return ol(Xc(e, {
			protocols: [...t.protocols ?? []],
			...t.headers ? { headers: { ...t.headers } } : {},
			...t.cookies ? { cookies: t.cookies } : {},
			...t.WebSocket ? { WebSocket: t.WebSocket } : {}
		}), n);
	} };
}
function al(e, t) {
	if (!t) throw new n("INVALID_CONFIGURATION", "Streamable HTTP requires a fetch implementation", { phase: "transport/http" });
	let r = sl(e);
	return async (e, i) => {
		let a = cl(e, r);
		for (let o = 0; o <= 5; o += 1) {
			let s = await t(e, {
				...i,
				redirect: "manual"
			});
			if (s.type === "opaqueredirect") throw new n("INVALID_CONFIGURATION", "ACP HTTP redirects are opaque in browsers; configure a redirect-free endpoint", { phase: "transport/redirect" });
			if (!ll(s.status)) return s;
			let c = s.headers.get("location");
			if (!c) return s;
			let l = new URL(c, a);
			if (l.origin !== r.origin) throw new n("INVALID_CONFIGURATION", `ACP HTTP redirect crossed an origin boundary: ${l.origin}`, { phase: "transport/redirect" });
			if (o === 5) throw new n("INVALID_CONFIGURATION", "ACP HTTP exceeded the redirect limit", { phase: "transport/redirect" });
			e = l.href, a = l;
		}
		throw Error("Unreachable redirect state");
	};
}
function ol(e, t) {
	let r = e.readable.getReader(), i = e.writable.getWriter(), a, o = !1, s = (e) => {
		if (!o) {
			o = !0, t.removeEventListener("abort", c);
			try {
				a?.error(e);
			} catch {}
			i.abort(e).catch(() => r.cancel(e)).catch(() => void 0);
		}
	}, c = () => s(t.reason);
	return t.addEventListener("abort", c, { once: !0 }), {
		readable: new ReadableStream({
			start(e) {
				a = e, t.aborted && s(t.reason);
			},
			async pull(e) {
				if (o) return;
				let i = await r.read();
				if (i.done) {
					o = !0, t.removeEventListener("abort", c), e.close();
					return;
				}
				if (!nn(i.value)) {
					s(new n("PROTOCOL_VIOLATION", "ACP wire message exceeded the 2 MiB decoded input limit", { phase: "transport/input" }));
					return;
				}
				e.enqueue(i.value);
			},
			cancel(e) {
				s(e);
			}
		}),
		writable: new WritableStream({
			write(e) {
				if (o) throw Error("ACP transport lifetime has ended");
				if (!nn(e)) throw new n("PROTOCOL_VIOLATION", "ACP wire message exceeded the 2 MiB decoded output limit", { phase: "transport/output" });
				return i.write(e);
			},
			async close() {
				o || (o = !0, t.removeEventListener("abort", c), await i.close());
			},
			abort(e) {
				s(e);
			}
		})
	};
}
function sl(e) {
	try {
		return new URL(e, globalThis.location === void 0 ? void 0 : globalThis.location.href);
	} catch (t) {
		throw new n("INVALID_CONFIGURATION", `ACP HTTP endpoint must be an absolute URL: ${e}`, {
			cause: t,
			phase: "transport/http"
		});
	}
}
function cl(e, t) {
	return typeof e == "string" ? new URL(e, t) : e instanceof URL ? e : new URL(e.url, t);
}
function ll(e) {
	return e >= 300 && e <= 399;
}
//#endregion
//#region src/standalone.tsx
var ul = 1048576, dl = 256, fl = /^[A-Za-z0-9+/_-]+={0,2}$/, pl = /* @__PURE__ */ new WeakMap(), ml = /* @__PURE__ */ new WeakMap();
function hl(e, t) {
	if (pl.has(e)) throw Error("pretty-aui: this target is already mounted");
	let n = Object.hasOwn(t, "options");
	if (n === Object.hasOwn(t, "controller")) throw TypeError("pretty-aui: mountChat requires exactly one of options or controller");
	t.styleNonce !== void 0 && gl(t.styleNonce);
	let r = ml.get(e);
	if (e.shadowRoot && e.shadowRoot !== r) throw Error("pretty-aui: mountChat requires a target without an existing shadow root");
	let i = r ?? e.attachShadow({ mode: "open" });
	ml.set(e, i);
	let a = document.createElement("style");
	t.styleNonce !== void 0 && (a.nonce = t.styleNonce), a.textContent = vc;
	let o = document.createElement("div");
	o.className = "pretty-aui-standalone-root", i.append(a, o);
	let s = {
		shadow: i,
		style: a,
		container: o
	};
	pl.set(e, s);
	let { surface: c, colorScheme: l, labels: u } = t, d = n ? cn(t.options) : t.controller, f = zt(o);
	f.render(/* @__PURE__ */ Z(Lo, {
		controller: d,
		surface: c,
		colorScheme: l,
		labels: u
	}));
	let p = !1, m, h = async () => {
		if (!p) {
			p = !0, m?.disconnect();
			try {
				f.unmount();
			} finally {
				try {
					n && await d.destroy();
				} finally {
					pl.get(e) === s && (a.remove(), o.remove(), pl.delete(e));
				}
			}
		}
	};
	return typeof MutationObserver < "u" && (m = yl(e, () => void h())), {
		controller: d,
		ready: d.ready,
		setDraft(e, t) {
			if (_l(p), e.length > ul) throw RangeError(`pretty-aui: draft exceeds ${ul} characters`);
			let n = vl(i);
			(Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")?.set)?.call(n, e), n.dispatchEvent(new Event("input", { bubbles: !0 })), t?.focus && n.focus();
		},
		focusComposer() {
			_l(p), vl(i).focus();
		},
		unmount: h
	};
}
function gl(e) {
	if (e.length === 0 || e.length > dl || !fl.test(e)) throw TypeError("pretty-aui: styleNonce is not a valid CSP nonce");
}
function _l(e) {
	if (e) throw Error("pretty-aui: mount has been unmounted");
}
function vl(e) {
	let t = e.querySelector("[data-pretty-aui-slot=\"composer-input\"] textarea");
	if (!t) throw Error("pretty-aui: composer is not mounted yet");
	return t;
}
function yl(e, t) {
	let n = e.isConnected, r = new MutationObserver(() => {
		if (n && !e.isConnected) {
			t();
			return;
		}
		i();
	}), i = () => {
		if (r.disconnect(), !e.isConnected) {
			r.observe(e.ownerDocument.documentElement, {
				childList: !0,
				subtree: !0
			});
			return;
		}
		n = !0;
		let t = e;
		for (;;) {
			if (t.parentNode) {
				r.observe(t.parentNode, { childList: !0 }), t = t.parentNode;
				continue;
			}
			let e = t.getRootNode();
			if (e instanceof ShadowRoot) {
				t = e.host;
				continue;
			}
			break;
		}
	};
	return i(), r;
}
//#endregion
export { n as PrettyAuiError, cn as createChat, rl as createStreamableHttpConnector, il as createWebSocketConnector, hl as mountChat };

//# sourceMappingURL=pretty-aui.js.map