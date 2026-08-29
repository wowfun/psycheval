globalThis.__zod_globalConfig ??= {}, globalThis.__zod_globalConfig.jitless = !0;
import { C as e, G as t, S as n, U as r, W as i, _ as a, a as o, c as s, d as c, f as l, g as u, h as d, i as f, l as p, m, n as h, o as g, p as _, r as v, s as y, t as b, u as x, w as S, x as ee } from "./chunks/types.js";
//#region node_modules/.pnpm/preact@10.29.8/node_modules/preact/dist/preact.module.js
var C, w, te, T, ne, re, ie, ae, oe, se, ce, le, ue, de, fe, E = {}, pe = [], me = /acit|ex(?:s|g|n|p|$)|rph|grid|ows|mnc|ntw|ine[ch]|zoo|^ord|itera/i, he = Array.isArray;
function ge(e, t) {
	for (var n in t) e[n] = t[n];
	return e;
}
function _e(e) {
	e && e.parentNode && e.parentNode.removeChild(e);
}
function ve(e, t, n) {
	var r, i, a, o = {};
	for (a in t) a == "key" ? r = t[a] : a == "ref" ? i = t[a] : o[a] = t[a];
	if (arguments.length > 2 && (o.children = arguments.length > 3 ? C.call(arguments, 2) : n), typeof e == "function" && e.defaultProps != null) for (a in e.defaultProps) o[a] === void 0 && (o[a] = e.defaultProps[a]);
	return ye(e, o, r, i, null);
}
function ye(e, t, n, r, i) {
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
	return i == null && w.vnode != null && w.vnode(a), a;
}
function D(e) {
	return e.children;
}
function O(e, t) {
	this.props = e, this.context = t;
}
function k(e, t) {
	if (t == null) return e.__ ? k(e.__, e.__i + 1) : null;
	for (var n; t < e.__k.length; t++) if ((n = e.__k[t]) != null && n.__e != null) return n.__e;
	return typeof e.type == "function" ? k(e) : null;
}
function be(e) {
	if (e.__P && e.__d) {
		var t = e.__v, n = t.__e, r = [], i = [], a = ge({}, t);
		a.__v = t.__v + 1, w.vnode && w.vnode(a), Ae(e.__P, a, t, e.__n, e.__P.namespaceURI, 32 & t.__u ? [n] : null, r, n ?? k(t), !!(32 & t.__u), i), a.__v = t.__v, a.__.__k[a.__i] = a, Me(r, a, i), t.__e = t.__ = null, a.__e != n && A(a);
	}
}
function A(e) {
	if ((e = e.__) != null && e.__c != null) return e.__e = e.__c.base = null, e.__k.some(function(t) {
		if (t != null && t.__e != null) return e.__e = e.__c.base = t.__e;
	}), A(e);
}
function xe(e) {
	(!e.__d && (e.__d = !0) && T.push(e) && !j.__r++ || ne != w.debounceRendering) && ((ne = w.debounceRendering) || re)(j);
}
function j() {
	try {
		for (var e, t = 1; T.length;) T.length > t && T.sort(ie), e = T.shift(), t = T.length, be(e);
	} finally {
		T.length = j.__r = 0;
	}
}
function Se(e, t, n, r, i, a, o, s, c, l, u) {
	var d, f, p, m, h, g, _ = r && r.__k || pe, v = t.length;
	for (c = Ce(n, t, _, c, v), d = 0; d < v; d++) (p = n.__k[d]) != null && (f = p.__i != -1 && _[p.__i] || E, p.__i = d, g = Ae(e, p, f, i, a, o, s, c, l, u), m = p.__e, p.ref && f.ref != p.ref && (f.ref && Fe(f.ref, null, p), u.push(p.ref, p.__c || m, p)), h == null && m != null && (h = m), 4 & p.__u ? (c = we(p, c, e), f.__e && (f.__e = null)) : typeof p.type == "function" && g !== void 0 ? c = g : m && (c = m.nextSibling), p.__u &= -7);
	return n.__e = h, c;
}
function Ce(e, t, n, r, i) {
	var a, o, s, c, l, u = n.length, d = u, f = 0;
	for (e.__k = Array(i), a = 0; a < i; a++) (o = t[a]) != null && typeof o != "boolean" && typeof o != "function" ? (typeof o == "string" || typeof o == "number" || typeof o == "bigint" || o.constructor == String ? o = e.__k[a] = ye(null, o, null, null, null) : he(o) ? o = e.__k[a] = ye(D, { children: o }, null, null, null) : o.constructor === void 0 && o.__b > 0 ? o = e.__k[a] = ye(o.type, o.props, o.key, o.ref ? o.ref : null, o.__v) : e.__k[a] = o, c = a + f, o.__ = e, o.__b = e.__b + 1, s = null, (l = o.__i = Ee(o, n, c, d)) != -1 && (d--, (s = n[l]) && (s.__u |= 2)), s == null || s.__v == null ? (l == -1 && (i > u ? f-- : i < u && f++), typeof o.type != "function" && (o.__u |= 4)) : l != c && (l == c - 1 ? f-- : l == c + 1 ? f++ : (l > c ? f-- : f++, o.__u |= 4))) : e.__k[a] = null;
	if (d) for (a = 0; a < u; a++) (s = n[a]) != null && !(2 & s.__u) && (s.__e == r && (r = k(s)), Ie(s, s));
	return r;
}
function we(e, t, n) {
	var r, i;
	if (typeof e.type == "function") {
		for (r = e.__k, i = 0; r && i < r.length; i++) r[i] && (r[i].__ = e, t = we(r[i], t, n));
		return t;
	}
	e.__e != t && (t && e.type && !t.parentNode && (t = k(e)), t = n.insertBefore(e.__e, t || null));
	do
		t &&= t.nextSibling;
	while (t != null && t.nodeType == 8);
	return t;
}
function Te(e, t) {
	return t ||= [], e == null || typeof e == "boolean" || (he(e) ? e.some(function(e) {
		Te(e, t);
	}) : t.push(e)), t;
}
function Ee(e, t, n, r) {
	var i, a, o, s = e.key, c = e.type, l = t[n], u = l != null && !(2 & l.__u);
	if (l === null && s == null || u && s == l.key && c == l.type) return n;
	if (r > +!!u) {
		for (i = n - 1, a = n + 1; i >= 0 || a < t.length;) if ((l = t[o = i >= 0 ? i-- : a++]) != null && !(2 & l.__u) && s == l.key && c == l.type) return o;
	}
	return -1;
}
function De(e, t, n) {
	t[0] == "-" ? e.setProperty(t, n ?? "") : e[t] = n == null ? "" : typeof n != "number" || me.test(t) ? n : n + "px";
}
function Oe(e, t, n, r, i) {
	var a, o;
	n: if (t == "style") {
		if (typeof n == "string") e.style.cssText = n;
		else {
			if (typeof r == "string" && (e.style.cssText = r = ""), r) for (t in r) n && t in n || De(e.style, t, "");
			if (n) for (t in n) r && n[t] == r[t] || De(e.style, t, n[t]);
		}
	} else if (t[0] == "o" && t[1] == "n") a = t != (t = t.replace(ce, "$1")), o = t.toLowerCase(), t = o in e || t == "onFocusOut" || t == "onFocusIn" ? o.slice(2) : t.slice(2), e.l ||= {}, e.l[t + a] = n, n ? r ? n[se] = r[se] : (n[se] = le, e.addEventListener(t, a ? de : ue, a)) : e.removeEventListener(t, a ? de : ue, a);
	else {
		if (i == "http://www.w3.org/2000/svg") t = t.replace(/xlink(H|:h)/, "h").replace(/sName$/, "s");
		else if (t != "width" && t != "height" && t != "href" && t != "list" && t != "form" && t != "tabIndex" && t != "download" && t != "rowSpan" && t != "colSpan" && t != "role" && t != "popover" && t in e) try {
			e[t] = n ?? "";
			break n;
		} catch {}
		typeof n == "function" || (n == null || !1 === n && t[4] != "-" ? e.removeAttribute(t) : e.setAttribute(t, t == "popover" && n == 1 ? "" : n));
	}
}
function ke(e) {
	return function(t) {
		if (this.l) {
			var n = this.l[t.type + e];
			if (t[oe] == null) t[oe] = le++;
			else if (t[oe] < n[se]) return;
			return n(w.event ? w.event(t) : t);
		}
	};
}
function Ae(e, t, n, r, i, a, o, s, c, l) {
	var u, d, f, p, m, h, g, _, v, y, b, x, S, ee, C, te, T = t.type;
	if (t.constructor !== void 0) return null;
	128 & n.__u && (c = !!(32 & n.__u), a = [s = t.__e = n.__e]), (u = w.__b) && u(t);
	n: if (typeof T == "function") {
		d = o.length;
		try {
			if (v = t.props, y = T.prototype && T.prototype.render, b = (u = T.contextType) && r[u.__c], x = u ? b ? b.props.value : u.__ : r, n.__c ? _ = (f = t.__c = n.__c).__ = f.__E : (y ? t.__c = f = new T(v, x) : (t.__c = f = new O(v, x), f.constructor = T, f.render = Le), b && b.sub(f), f.state || (f.state = {}), f.__n = r, p = f.__d = !0, f.__h = [], f._sb = []), y && f.__s == null && (f.__s = f.state), y && T.getDerivedStateFromProps != null && (f.__s == f.state && (f.__s = ge({}, f.__s)), ge(f.__s, T.getDerivedStateFromProps(v, f.__s))), m = f.props, h = f.state, f.__v = t, p) y && T.getDerivedStateFromProps == null && f.componentWillMount != null && f.componentWillMount(), y && f.componentDidMount != null && f.__h.push(f.componentDidMount);
			else {
				if (y && T.getDerivedStateFromProps == null && v !== m && f.componentWillReceiveProps != null && f.componentWillReceiveProps(v, x), t.__v == n.__v || !f.__e && f.shouldComponentUpdate != null && !1 === f.shouldComponentUpdate(v, f.__s, x)) {
					t.__v != n.__v && (f.props = v, f.state = f.__s, f.__d = !1), t.__e = n.__e, t.__k = n.__k, t.__k.some(function(e) {
						e && (e.__ = t);
					}), pe.push.apply(f.__h, f._sb), f._sb = [], f.__h.length && o.push(f), s = k(n);
					break n;
				}
				f.componentWillUpdate != null && f.componentWillUpdate(v, f.__s, x), y && f.componentDidUpdate != null && f.__h.push(function() {
					f.componentDidUpdate(m, h, g);
				});
			}
			if (f.context = x, f.props = v, f.__P = e, f.__e = !1, S = w.__r, ee = 0, y) f.state = f.__s, f.__d = !1, S && S(t), u = f.render(f.props, f.state, f.context), pe.push.apply(f.__h, f._sb), f._sb = [];
			else do
				f.__d = !1, S && S(t), u = f.render(f.props, f.state, f.context), f.state = f.__s;
			while (f.__d && ++ee < 25);
			f.state = f.__s, f.getChildContext != null && (r = ge(ge({}, r), f.getChildContext())), y && !p && f.getSnapshotBeforeUpdate != null && (g = f.getSnapshotBeforeUpdate(m, h)), C = u != null && u.type === D && u.key == null ? Ne(u.props.children) : u, s = Se(e, he(C) ? C : [C], t, n, r, i, a, o, s, c, l), f.base = t.__e, t.__u &= -161, f.__h.length && o.push(f), _ && (f.__E = f.__ = null);
		} catch (e) {
			if (o.length = d, t.__v = null, c || a != null) {
				if (e.then) {
					for (t.__u |= c ? 160 : 128; s && s.nodeType == 8 && s.nextSibling;) s = s.nextSibling;
					a != null && (a[a.indexOf(s)] = null), t.__e = s;
				} else if (a != null) for (te = a.length; te--;) _e(a[te]);
			} else t.__e = n.__e;
			t.__k ??= n.__k || [], e.then || je(t), w.__e(e, t, n);
		}
	} else a == null && t.__v == n.__v ? (t.__k = n.__k, t.__e = n.__e) : s = t.__e = Pe(n.__e, t, n, r, i, a, o, c, l);
	return (u = w.diffed) && u(t), 128 & t.__u ? void 0 : s;
}
function je(e) {
	e && (e.__c && (e.__c.__e = !0), e.__k && e.__k.some(je));
}
function Me(e, t, n) {
	for (var r = 0; r < n.length; r++) Fe(n[r], n[++r], n[++r]);
	w.__c && w.__c(t, e), e.some(function(t) {
		try {
			e = t.__h, t.__h = [], e.some(function(e) {
				e.call(t);
			});
		} catch (e) {
			w.__e(e, t.__v);
		}
	});
}
function Ne(e) {
	return typeof e != "object" || !e || e.__b > 0 ? e : he(e) ? e.map(Ne) : e.constructor === void 0 ? ge({}, e) : null;
}
function Pe(e, t, n, r, i, a, o, s, c) {
	var l, u, d, f, p, m, h, g = n.props || E, _ = t.props, v = t.type;
	if (v == "svg" ? i = "http://www.w3.org/2000/svg" : v == "math" ? i = "http://www.w3.org/1998/Math/MathML" : i ||= "http://www.w3.org/1999/xhtml", a != null) {
		for (l = 0; l < a.length; l++) if ((p = a[l]) && "setAttribute" in p == !!v && (v ? p.localName == v : p.nodeType == 3)) {
			e = p, a[l] = null;
			break;
		}
	}
	if (e == null) {
		if (v == null) return document.createTextNode(_);
		e = document.createElementNS(i, v, _.is && _), s &&= (w.__m && w.__m(t, a), !1), a = null;
	}
	if (v == null) g === _ || s && e.data == _ || (e.data = _);
	else {
		if (a = v == "textarea" && _.defaultValue != null ? null : a && C.call(e.childNodes), !s && a != null) for (g = {}, l = 0; l < e.attributes.length; l++) g[(p = e.attributes[l]).name] = p.value;
		for (l in g) p = g[l], l == "dangerouslySetInnerHTML" ? d = p : l == "children" || l in _ || l == "value" && "defaultValue" in _ || l == "checked" && "defaultChecked" in _ || Oe(e, l, null, p, i);
		for (l in _) p = _[l], l == "children" ? f = p : l == "dangerouslySetInnerHTML" ? u = p : l == "value" ? m = p : l == "checked" ? h = p : s && typeof p != "function" || g[l] === p || Oe(e, l, p, g[l], i);
		if (u) s || d && (u.__html == d.__html || u.__html == e.innerHTML) || (e.innerHTML = u.__html), t.__k = [];
		else if (d && (e.innerHTML = ""), Se(t.type == "template" ? e.content : e, he(f) ? f : [f], t, n, r, v == "foreignObject" ? "http://www.w3.org/1999/xhtml" : i, a, o, a ? a[0] : n.__k && k(n, 0), s, c), a != null) for (l = a.length; l--;) _e(a[l]);
		s && v != "textarea" || (l = "value", v == "progress" && m == null ? e.removeAttribute("value") : m != null && (m !== e[l] || v == "progress" && !m || v == "option" && m != g[l]) && Oe(e, l, m, g[l], i), l = "checked", h != null && h != e[l] && Oe(e, l, h, g[l], i));
	}
	return e;
}
function Fe(e, t, n) {
	try {
		if (typeof e == "function") {
			var r = typeof e.__u == "function";
			r && e.__u(), r && t == null || (e.__u = e(t));
		} else e.current = t;
	} catch (e) {
		w.__e(e, n);
	}
}
function Ie(e, t, n) {
	var r, i;
	if (w.unmount && w.unmount(e), (r = e.ref) && (r.current && r.current != e.__e || Fe(r, null, t)), (r = e.__c) != null) {
		if (r.componentWillUnmount) try {
			r.componentWillUnmount();
		} catch (e) {
			w.__e(e, t);
		}
		r.base = r.__P = r.__n = null;
	}
	if (r = e.__k) for (i = 0; i < r.length; i++) r[i] && Ie(r[i], t, n || typeof e.type != "function");
	n || _e(e.__e), e.__c = e.__ = e.__e = void 0;
}
function Le(e, t, n) {
	return this.constructor(e, n);
}
function Re(e, t, n) {
	var r, i, a, o;
	t == document && (t = document.documentElement), w.__ && w.__(e, t), i = (r = typeof n == "function") ? null : n && n.__k || t.__k, a = [], o = [], Ae(t, e = (!r && n || t).__k = ve(D, null, [e]), i || E, E, t.namespaceURI, !r && n ? [n] : i ? null : t.firstChild ? C.call(t.childNodes) : null, a, !r && n ? n : i ? i.__e : t.firstChild, r, o), Me(a, e, o), e.props.children = null;
}
function ze(e) {
	function t(e) {
		var n, r;
		return this.getChildContext || (n = /* @__PURE__ */ new Set(), (r = {})[t.__c] = this, this.getChildContext = function() {
			return r;
		}, this.componentWillUnmount = function() {
			n = null;
		}, this.shouldComponentUpdate = function(e) {
			this.props.value != e.value && n.forEach(function(e) {
				e.__e = !0, xe(e);
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
C = pe.slice, w = { __e: function(e, t, n, r) {
	for (var i, a, o; t = t.__;) if ((i = t.__c) && !i.__) try {
		if ((a = i.constructor) && a.getDerivedStateFromError != null && (i.setState(a.getDerivedStateFromError(e)), o = i.__d), i.componentDidCatch != null && (i.componentDidCatch(e, r || {}), o = i.__d), o) return i.__E = i;
	} catch (t) {
		e = t;
	}
	throw e;
} }, te = 0, O.prototype.setState = function(e, t) {
	var n = this.__s != null && this.__s != this.state ? this.__s : this.__s = ge({}, this.state);
	typeof e == "function" && (e = e(ge({}, n), this.props)), e && ge(n, e), e != null && this.__v && (t && this._sb.push(t), xe(this));
}, O.prototype.forceUpdate = function(e) {
	this.__v && (this.__e = !0, e && this.__h.push(e), xe(this));
}, O.prototype.render = D, T = [], re = typeof Promise == "function" ? Promise.prototype.then.bind(Promise.resolve()) : setTimeout, ie = function(e, t) {
	return e.__v.__b - t.__v.__b;
}, j.__r = 0, ae = Math.random().toString(8), oe = "__d" + ae, se = "__a" + ae, ce = /(PointerCapture)$|Capture$/i, le = 0, ue = ke(!1), de = ke(!0), fe = 0;
//#endregion
//#region node_modules/.pnpm/preact@10.29.8/node_modules/preact/hooks/dist/hooks.module.js
var Be, M, Ve, He, Ue = 0, We = [], N = w, Ge = N.__b, Ke = N.__r, qe = N.diffed, Je = N.__c, Ye = N.unmount, Xe = N.__;
function P(e, t) {
	N.__h && N.__h(M, e, Ue || t), Ue = 0;
	var n = M.__H || (M.__H = {
		__: [],
		__h: []
	});
	return e >= n.__.length && n.__.push({}), n.__[e];
}
function F(e) {
	return Ue = 1, Ze(ct, e);
}
function Ze(e, t, n) {
	var r = P(Be++, 2);
	if (r.t = e, !r.__c && (r.__ = [n ? n(t) : ct(void 0, t), function(e) {
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
	var n = P(Be++, 3);
	!N.__s && st(n.__H, t) && (n.__ = e, n.u = t, M.__H.__h.push(n));
}
function Qe(e, t) {
	var n = P(Be++, 4);
	!N.__s && st(n.__H, t) && (n.__ = e, n.u = t, M.__h.push(n));
}
function L(e) {
	return Ue = 5, $e(function() {
		return { current: e };
	}, []);
}
function $e(e, t) {
	var n = P(Be++, 7);
	return st(n.__H, t) && (n.__ = e(), n.__H = t, n.__h = e), n.__;
}
function et(e, t) {
	return Ue = 8, $e(function() {
		return e;
	}, t);
}
function tt(e) {
	var t = M.context[e.__c], n = P(Be++, 9);
	return n.c = e, t ? (n.__ ?? (n.__ = !0, t.sub(M)), t.props.value) : e.__;
}
function nt() {
	var e = P(Be++, 11);
	if (!e.__) {
		for (var t = M.__v; t !== null && !t.__m && t.__ !== null;) t = t.__;
		var n = t.__m || (t.__m = [0, 0]);
		e.__ = "P" + n[0] + "-" + n[1]++;
	}
	return e.__;
}
function rt() {
	for (var e; e = We.shift();) {
		var t = e.__H;
		if (e.__P && t) try {
			t.__h.some(at), t.__h.some(ot), t.__h = [];
		} catch (n) {
			t.__h = [], N.__e(n, e.__v);
		}
	}
}
N.__b = function(e) {
	M = null, Ge && Ge(e);
}, N.__ = function(e, t) {
	e && t.__k && t.__k.__m && (e.__m = t.__k.__m), Xe && Xe(e, t);
}, N.__r = function(e) {
	Ke && Ke(e), Be = 0;
	var t = (M = e.__c).__H;
	t && (Ve === M ? (t.__h = [], M.__h = [], t.__.some(function(e) {
		e.__N && (e.__ = e.__N), e.u = e.__N = void 0;
	})) : (t.__h.some(at), t.__h.some(ot), t.__h = [], Be = 0)), Ve = M;
}, N.diffed = function(e) {
	qe && qe(e);
	var t = e.__c;
	t && t.__H && (t.__H.__h.length && (We.push(t) !== 1 && He === N.requestAnimationFrame || ((He = N.requestAnimationFrame) || R)(rt)), t.__H.__.some(function(e) {
		e.u &&= (e.__H = e.u, void 0);
	})), Ve = M = null;
}, N.__c = function(e, t) {
	t.some(function(e) {
		try {
			e.__h.some(at), e.__h = e.__h.filter(function(e) {
				return !e.__ || ot(e);
			});
		} catch (n) {
			t.some(function(e) {
				e.__h &&= [];
			}), t = [], N.__e(n, e.__v);
		}
	}), Je && Je(e, t);
}, N.unmount = function(e) {
	Ye && Ye(e);
	var t, n = e.__c;
	n && n.__H && (n.__H.__.some(function(e) {
		try {
			at(e);
		} catch (e) {
			t = e;
		}
	}), n.__H = void 0, t && N.__e(t, n.__v));
};
var it = typeof requestAnimationFrame == "function";
function R(e) {
	var t, n = function() {
		clearTimeout(r), it && cancelAnimationFrame(t), setTimeout(e);
	}, r = setTimeout(n, 35);
	it && (t = requestAnimationFrame(n));
}
function at(e) {
	var t = M, n = e.__c;
	typeof n == "function" && (e.__c = void 0, n()), M = t;
}
function ot(e) {
	var t = M;
	e.__c = e.__(), M = t;
}
function st(e, t) {
	return !e || e.length !== t.length || t.some(function(t, n) {
		return t !== e[n];
	});
}
function ct(e, t) {
	return typeof t == "function" ? t(e) : t;
}
//#endregion
//#region node_modules/.pnpm/preact@10.29.8/node_modules/preact/compat/dist/compat.module.js
function lt(e, t) {
	for (var n in t) e[n] = t[n];
	return e;
}
function ut(e, t) {
	for (var n in e) if (n !== "__source" && !(n in t)) return !0;
	for (var r in t) if (r !== "__source" && e[r] !== t[r]) return !0;
	return !1;
}
function dt(e, t) {
	var n = t(), r = F({ t: {
		__: n,
		u: t
	} }), i = r[0].t, a = r[1];
	return Qe(function() {
		i.__ = n, i.u = t, ft(i) && a({ t: i });
	}, [
		e,
		n,
		t
	]), I(function() {
		return ft(i) && a({ t: i }), e(function() {
			ft(i) && a({ t: i });
		});
	}, [e]), n;
}
function ft(e) {
	try {
		return !((t = e.__) === (n = e.u()) && (t !== 0 || 1 / t == 1 / n) || t != t && n != n);
	} catch {
		return !0;
	}
	var t, n;
}
function pt(e, t) {
	this.props = e, this.context = t;
}
function mt(e, t) {
	function n(e) {
		var n = this.props.ref;
		return n != e.ref && n && (typeof n == "function" ? n(null) : n.current = null), t ? !t(this.props, e) || n != e.ref : ut(this.props, e);
	}
	function r(t) {
		return this.shouldComponentUpdate = n, ve(e, t);
	}
	return r.displayName = "Memo(" + (e.displayName || e.name) + ")", r.__f = r.prototype.isReactComponent = !0, r.type = e, r;
}
(pt.prototype = new O()).isPureReactComponent = !0, pt.prototype.shouldComponentUpdate = function(e, t) {
	return ut(this.props, e) || ut(this.state, t);
};
var ht = w.__b;
w.__b = function(e) {
	e.type && e.type.__f && e.ref && (e.props.ref = e.ref, e.ref = null), ht && ht(e);
}, typeof Symbol < "u" && Symbol.for;
var gt = w.__e;
w.__e = function(e, t, n, r) {
	if (e.then) {
		for (var i, a = t; a = a.__;) if ((i = a.__c) && i.__c) return t.__e ?? (t.__e = n.__e, t.__k = n.__k || []), i.__c(e, t);
	}
	gt(e, t, n, r);
};
var _t = w.unmount;
function vt(e, t, n) {
	return e && (e.__c && e.__c.__H && (e.__c.__H.__.forEach(function(e) {
		typeof e.__c == "function" && e.__c();
	}), e.__c.__H = null), (e = lt({}, e)).__c != null && (e.__c.__P === n && (e.__c.__P = t), e.__c.__e = !0, e.__c = null), e.__k = e.__k && e.__k.map(function(e) {
		return vt(e, t, n);
	})), e;
}
function yt(e, t, n) {
	return e && n && (e.__v = null, e.__k = e.__k && e.__k.map(function(e) {
		return yt(e, t, n);
	}), e.__c && e.__c.__P === t && (e.__e && n.appendChild(e.__e), e.__c.__e = !0, e.__c.__P = n)), e;
}
function bt() {
	this.__u = 0, this.o = null, this.__b = null;
}
function xt(e) {
	var t = e.__ && e.__.__c;
	return t && t.__a && t.__a(e);
}
function St() {
	this.i = null, this.l = null;
}
w.unmount = function(e) {
	var t = e.__c;
	t && (t.__z = !0), t && t.__R && t.__R(), t && 32 & e.__u && (e.type = null), _t && _t(e);
}, (bt.prototype = new O()).__c = function(e, t) {
	var n = t.__c, r = this;
	r.o ??= [], r.o.push(n);
	var i = xt(r.__v), a = !1, o = function() {
		a || r.__z || (a = !0, n.__R = null, i ? i(c) : c());
	};
	n.__R = o;
	var s = n.__P;
	n.__P = null;
	var c = function() {
		if (!--r.__u) {
			if (r.state.__a) {
				var e = r.state.__a;
				r.__v.__k[0] = yt(e, e.__c.__P, e.__c.__O);
			}
			var t;
			for (r.setState({ __a: r.__b = null }); t = r.o.pop();) t.__P = s, t.forceUpdate();
		}
	};
	r.__u++ || 32 & t.__u || r.setState({ __a: r.__b = r.__v.__k[0] }), e.then(o, o);
}, bt.prototype.componentWillUnmount = function() {
	this.o = [];
}, bt.prototype.render = function(e, t) {
	if (this.__b) {
		if (this.__v.__k) {
			var n = document.createElement("div"), r = this.__v.__k[0].__c;
			this.__v.__k[0] = vt(this.__b, n, r.__O = r.__P);
		}
		this.__b = null;
	}
	var i = t.__a && ve(D, null, e.fallback);
	return i && (i.__u &= -33), [ve(D, null, t.__a ? null : e.children), i];
};
var Ct = function(e, t, n) {
	if (++n[1] === n[0] && e.l.delete(t), e.props.revealOrder && (e.props.revealOrder[0] !== "t" || !e.l.size)) for (n = e.i; n;) {
		for (; n.length > 3;) n.pop()();
		if (n[1] < n[0]) break;
		e.i = n = n[2];
	}
};
(St.prototype = new O()).__a = function(e) {
	var t = this, n = xt(t.__v), r = t.l.get(e);
	return r[0]++, function(i) {
		var a = function() {
			t.props.revealOrder ? (r.push(i), Ct(t, e, r)) : i();
		};
		n ? n(a) : a();
	};
}, St.prototype.render = function(e) {
	this.i = null, this.l = /* @__PURE__ */ new Map();
	var t = Te(e.children);
	e.revealOrder && e.revealOrder[0] === "b" && t.reverse();
	for (var n = t.length; n--;) this.l.set(t[n], this.i = [
		1,
		0,
		this.i
	]);
	return e.children;
}, St.prototype.componentDidUpdate = St.prototype.componentDidMount = function() {
	var e = this;
	this.l.forEach(function(t, n) {
		Ct(e, n, t);
	});
};
var wt = typeof Symbol < "u" && Symbol.for && Symbol.for("react.element") || 60103, Tt = /^(?:accent|alignment|arabic|baseline|cap|clip(?!PathU)|color|dominant|fill|flood|font|glyph(?!R)|horiz|image(!S)|letter|lighting|marker(?!H|W|U)|overline|paint|pointer|shape|stop|strikethrough|stroke|text(?!L)|transform|underline|unicode|units|v|vector|vert|word|writing|x(?!C))[A-Z]/, Et = /^on(Ani|Tra|Tou|BeforeInp|Compo)/, Dt = /[A-Z0-9]/g, Ot = typeof document < "u", kt = function(e) {
	return (typeof Symbol < "u" && typeof Symbol() == "symbol" ? /fil|che|rad/ : /fil|che|ra/).test(e);
};
function At(e, t, n) {
	return t.__k ?? (t.textContent = ""), Re(e, t), typeof n == "function" && n(), e ? e.__c : null;
}
O.prototype.isReactComponent = !0, [
	"componentWillMount",
	"componentWillReceiveProps",
	"componentWillUpdate"
].forEach(function(e) {
	Object.defineProperty(O.prototype, e, {
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
var jt = w.event;
w.event = function(e) {
	return jt && (e = jt(e)), e.persist = function() {}, e.isPropagationStopped = function() {
		return this.cancelBubble;
	}, e.isDefaultPrevented = function() {
		return this.defaultPrevented;
	}, e.nativeEvent = e;
};
var Mt = {
	configurable: !0,
	get: function() {
		return this.class;
	}
}, Nt = w.vnode;
w.vnode = function(e) {
	typeof e.type == "string" && function(e) {
		var t = e.props, n = e.type, r = {}, i = n.indexOf("-") == -1;
		for (var a in t) {
			var o = t[a];
			if (!(a === "value" && "defaultValue" in t && o == null || Ot && a === "children" && n === "noscript" || a === "class" || a === "className")) {
				var s = a.toLowerCase();
				a === "defaultValue" && "value" in t && t.value == null ? a = "value" : a === "download" && !0 === o ? o = "" : s === "translate" && o === "no" ? o = !1 : s[0] === "o" && s[1] === "n" ? s === "ondoubleclick" ? a = "ondblclick" : s !== "onchange" || n !== "input" && n !== "textarea" || kt(t.type) ? s === "onfocus" ? a = "onfocusin" : s === "onblur" ? a = "onfocusout" : Et.test(a) && (a = s) : s = a = "oninput" : i && Tt.test(a) ? a = a.replace(Dt, "-$&").toLowerCase() : o === null && (o = void 0), s === "oninput" && r[a = s] && (a = "oninputCapture"), r[a] = o;
			}
		}
		n == "select" && (r.multiple && Array.isArray(r.value) && (r.value = Te(t.children).forEach(function(e) {
			e.props.selected = r.value.indexOf(e.props.value) != -1;
		})), r.defaultValue != null && (r.value = Te(t.children).forEach(function(e) {
			e.props.selected = r.multiple ? r.defaultValue.indexOf(e.props.value) != -1 : r.defaultValue == e.props.value;
		}))), t.class && !t.className ? (r.class = t.class, Object.defineProperty(r, "className", Mt)) : t.className && (r.class = r.className = t.className), e.props = r;
	}(e), e.$$typeof = wt, Nt && Nt(e);
};
var Pt = w.__r;
w.__r = function(e) {
	Pt && Pt(e), e.__c;
};
var Ft = w.diffed;
w.diffed = function(e) {
	Ft && Ft(e);
	var t = e.props, n = e.__e;
	n != null && e.type === "textarea" && "value" in t && t.value !== n.value && (n.value = t.value == null ? "" : t.value);
};
function It(e) {
	return !!e.__k && (Re(null, e), !0);
}
//#endregion
//#region node_modules/.pnpm/preact@10.29.8/node_modules/preact/compat/client.mjs
function Lt(e) {
	return {
		render: function(t) {
			At(t, e);
		},
		unmount: function() {
			It(e);
		}
	};
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/line-buffer.js
var Rt = 10, zt = class {
	#e = [];
	push(e) {
		let t = [], n = 0, r = e.indexOf(Rt, n);
		for (; r !== -1;) t.push(this.#t(e.subarray(n, r))), n = r + 1, r = e.indexOf(Rt, n);
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
async function Bt(e) {
	let { sink: t, host: n } = e, r = u({ name: e.clientInfo.name });
	r = r.onRequest(a.client.session.requestPermission, async ({ params: e }) => {
		let n = e, r = await t.onPermission(e.sessionId, Gt(n), n);
		return y(r);
	}).onRequest(a.client.elicitation.create, async ({ params: e }) => {
		let n = e, r = await t.onElicitation("sessionId" in e && typeof e.sessionId == "string" ? e.sessionId : void 0, o(n), n);
		return f(r);
	}).onNotification(a.client.session.update, ({ params: e }) => {
		t.onProtocol(a.client.session.update, e), t.onUpdate(e.sessionId, e.update);
	}).onNotification(a.client.elicitation.complete, ({ params: e }) => {
		t.onProtocol(a.client.elicitation.complete, e), t.onElicitationComplete(e.elicitationId);
	});
	let s = n?.v1?.filesystem;
	s?.readTextFile && (r = r.onRequest(a.client.fs.readTextFile, async ({ params: e }) => await s.readTextFile(e))), s?.writeTextFile && (r = r.onRequest(a.client.fs.writeTextFile, async ({ params: e }) => await s.writeTextFile(e)));
	let c = n?.v1?.terminal;
	c && (r = r.onRequest(a.client.terminal.create, async ({ params: e }) => await c.create(e)).onRequest(a.client.terminal.output, async ({ params: e }) => await c.output(e)).onRequest(a.client.terminal.release, async ({ params: e }) => await c.release(e)).onRequest(a.client.terminal.waitForExit, async ({ params: e }) => await c.waitForExit(e)).onRequest(a.client.terminal.kill, async ({ params: e }) => await c.kill(e)));
	let d = r.connect(e.stream), p = !1;
	d.closed.then(() => {
		p || t.onDisconnect();
	});
	let m;
	try {
		m = await d.agent.request(a.agent.initialize, {
			protocolVersion: 1,
			clientInfo: {
				name: e.clientInfo.name,
				version: e.clientInfo.version,
				...e.clientInfo.title ? { title: e.clientInfo.title } : {}
			},
			clientCapabilities: {
				fs: {
					readTextFile: !!s?.readTextFile,
					writeTextFile: !!s?.writeTextFile
				},
				terminal: !!c,
				session: { configOptions: { boolean: {} } },
				auth: { terminal: !!n?.terminalAuth },
				elicitation: {
					form: {},
					url: {}
				}
			}
		});
	} catch (e) {
		throw d.close(e), new i("INITIALIZE_REJECTED", "ACP v1 initialization failed", {
			cause: e,
			protocol: 1,
			phase: "initialize",
			retryable: !0
		});
	}
	if (m.protocolVersion !== 1) throw d.close(), new i("PROTOCOL_VERSION_MISMATCH", `Requested ACP v1 but agent selected v${m.protocolVersion}`, {
		protocol: 1,
		phase: "initialize"
	});
	let h = m.agentCapabilities, g = h?.sessionCapabilities;
	return new Vt(d, {
		protocolVersion: 1,
		...m.agentInfo?.title || m.agentInfo?.name ? { agentName: m.agentInfo.title ?? m.agentInfo.name } : {},
		authMethods: l(m.authMethods),
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
	}, t, n, () => {
		p = !0;
	});
}
var Vt = class {
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
		v(e, this.initialized, 1, "session/new");
		let t = await b(() => this.connection.agent.request(a.agent.session.new, Ht(e)), 1, "session/new");
		return this.#e.set(t.sessionId, !t.configOptions?.length && !!t.modes), Wt(t.sessionId, t.configOptions, t.modes);
	}
	async openSession(e, t, n) {
		v(t, this.initialized, 1, "session/open");
		let r = {
			...Ht(t),
			sessionId: e
		};
		if (n === "all" && this.initialized.capabilities.loadSession) {
			let t = await b(() => this.connection.agent.request(a.agent.session.load, r), 1, "session/open");
			return this.#e.set(e, !t.configOptions?.length && !!t.modes), Wt(e, t.configOptions, t.modes);
		}
		if (!this.initialized.capabilities.resumeSession) throw new i("CAPABILITY_REQUIRED", "The agent cannot open existing sessions", {
			protocol: 1,
			phase: "session/resume"
		});
		let o = await b(() => this.connection.agent.request(a.agent.session.resume, r), 1, "session/open");
		return this.#e.set(e, !o.configOptions?.length && !!o.modes), Wt(e, o.configOptions, o.modes, n === "all");
	}
	async listSessions(e, t) {
		if (!this.initialized.capabilities.listSessions) throw new i("CAPABILITY_REQUIRED", "The agent does not support session/list", { protocol: 1 });
		let n = await this.connection.agent.request(a.agent.session.list, {
			cwd: e,
			...t ? { cursor: t } : {}
		});
		return d(n);
	}
	async deleteSession(e) {
		if (!this.initialized.capabilities.deleteSession) throw new i("CAPABILITY_REQUIRED", "The agent does not support session/delete", { protocol: 1 });
		await this.connection.agent.request(a.agent.session.delete, { sessionId: e }), this.#e.delete(e);
	}
	async closeSession(e) {
		if (!this.initialized.capabilities.closeSession) {
			this.#e.delete(e);
			return;
		}
		await this.connection.agent.request(a.agent.session.close, { sessionId: e }), this.#e.delete(e);
	}
	promptReady(e) {
		return !0;
	}
	async prompt(e, t, n) {
		let r = this.connection.agent.request(a.agent.session.prompt, {
			sessionId: e,
			prompt: t
		});
		return n(), (await r).stopReason;
	}
	async cancel(e) {
		await this.connection.agent.notify(a.agent.session.cancel, { sessionId: e });
	}
	async setConfigOption(e, t, n) {
		if (this.#e.get(e) && t === "mode" && typeof n == "string") return await this.connection.agent.request(a.agent.session.setMode, {
			sessionId: e,
			modeId: n
		}), [];
		let r = await this.connection.agent.request(a.agent.session.setConfigOption, {
			sessionId: e,
			configId: t,
			value: n,
			...typeof n == "boolean" ? { type: "boolean" } : {}
		});
		return _(r.configOptions);
	}
	async authenticate(e) {
		if (e.type === "terminal") {
			if (!this.host?.terminalAuth) throw new i("CAPABILITY_REQUIRED", "Terminal authentication needs a host handler", { protocol: 1 });
			await this.host.terminalAuth(e);
			return;
		}
		await this.connection.agent.request(a.agent.authenticate, { methodId: e.id });
	}
	async logout() {
		await this.connection.agent.request(a.agent.logout, {}), this.#e.clear();
	}
	async close(e) {
		this.markClosed(), this.#e.clear(), this.connection.close(e), await this.connection.closed;
	}
};
function Ht(e) {
	return {
		cwd: e.cwd,
		mcpServers: (e.mcpServers ?? []).map(Ut),
		...e.additionalDirectories?.length ? { additionalDirectories: [...e.additionalDirectories] } : {}
	};
}
function Ut(e) {
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
function Wt(e, t, n, r = !1) {
	let i = _(t);
	return {
		sessionId: e,
		configOptions: i.length ? i : m(n),
		...r ? { historyGap: r } : {}
	};
}
function Gt(e) {
	let t = c(e) ? e : {}, n = c(t.toolCall) ? t.toolCall : {};
	return {
		type: "permission",
		title: p(n.title) ?? "Permission required",
		options: g(t.options)
	};
}
//#endregion
//#region src/core/protocol/connect.ts
async function Kt(e) {
	if (e.protocol === 1) return qt(1, 1, e);
	if (e.protocol === 2) return qt(2, 1, e);
	let t = await e.connector.open({
		protocol: 2,
		attempt: 1,
		signal: e.signal
	}), n = Yt(t);
	try {
		return await Jt(n.stream, e);
	} catch (r) {
		if (n.negotiatedVersion() !== 1) throw r;
		return await Qt(t), qt(1, 2, e);
	}
}
async function qt(e, t, n) {
	let r = await n.connector.open({
		protocol: e,
		attempt: t,
		signal: n.signal
	});
	if (n.signal.aborted) throw await Qt(r), new i("CONNECTION_CLOSED", "Connection was cancelled", {
		protocol: e,
		retryable: !0
	});
	return e === 1 ? Bt({
		stream: r,
		sink: n.sink,
		clientInfo: n.clientInfo,
		...n.host ? { host: n.host } : {}
	}) : Jt(r, n);
}
async function Jt(e, t) {
	let { connectV2: n } = await import("./chunks/v2.js");
	return n({
		stream: e,
		sink: t.sink,
		clientInfo: t.clientInfo,
		...t.host ? { host: t.host } : {}
	});
}
function Yt(e) {
	let t, n, r = e.writable, i = e.readable, a = new WritableStream({
		async write(e) {
			let n = Xt(e);
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
				for (let e of i) !Zt(e) || e.id !== t || !Zt(e.result) || typeof e.result.protocolVersion == "number" && (n = e.result.protocolVersion);
				r.enqueue(e);
			} })),
			writable: a
		},
		negotiatedVersion: () => n
	};
}
function Xt(e) {
	let t = Array.isArray(e) ? e : [e];
	for (let e of t) if (Zt(e) && e.method === "initialize" && Object.hasOwn(e, "id")) return { id: e.id };
}
function Zt(e) {
	return typeof e == "object" && !!e && !Array.isArray(e);
}
async function Qt(e) {
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
var $t = 2097152;
function en(e, t = $t) {
	let n;
	try {
		n = JSON.stringify(e);
	} catch {
		return !1;
	}
	return n !== void 0 && tn(n, t) <= t;
}
function tn(e, t) {
	let n = 0;
	for (let r = 0; r < e.length; r += 1) {
		let i = e.charCodeAt(r);
		if (i <= 127 ? n += 1 : i <= 2047 ? n += 2 : i >= 55296 && i <= 56319 && r + 1 < e.length && e.charCodeAt(r + 1) >= 56320 && e.charCodeAt(r + 1) <= 57343 ? (n += 4, r += 1) : n += 3, n > t) return n;
	}
	return n;
}
//#endregion
//#region src/core/chat-controller.ts
var nn = {
	listSessions: !1,
	loadSession: !1,
	resumeSession: !1,
	closeSession: !1,
	deleteSession: !1
};
function rn(e) {
	return new an(e);
}
var an = class {
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
	#w = /* @__PURE__ */ new Map();
	#T;
	constructor(e) {
		this.#e = e, this.#i = sn(e.context), this.#f = {
			phase: "connecting",
			loadedSessions: [],
			historyGap: !1,
			activities: [],
			configOptions: [],
			commands: [],
			contextSelection: this.#ee(),
			interactions: [],
			authMethods: [],
			capabilities: nn,
			sessionTrail: []
		}, on(e.context) && (this.#n = e.context.subscribe(() => {
			this.#_ || this.#$();
		})), this.ready = this.#E(!0), this.ready.catch(() => void 0);
	}
	getSnapshot() {
		return this.#f;
	}
	subscribe(e) {
		return this.#t.add(e), () => this.#t.delete(e);
	}
	send(e) {
		this.#R();
		let t = this.#K();
		if (this.#w.has(t.sessionId)) throw new i("SESSION_BUSY", `Wait for the current operation on session '${t.sessionId}'`, {
			protocol: this.#d?.version,
			phase: "prompt"
		});
		if (t.activeTurn) throw new i("SESSION_BUSY", "Wait for the current turn to finish", {
			protocol: this.#d?.version,
			phase: "prompt"
		});
		if (t.phase !== "idle" || !this.#U().promptReady(t.sessionId)) throw new i("SESSION_BUSY", `Session '${t.sessionId}' is not ready for another prompt`, {
			protocol: this.#d?.version,
			phase: "prompt"
		});
		let n = ln(e);
		if (n.some((e) => e._meta !== null && e._meta !== void 0 && Object.hasOwn(e._meta, "pretty-aui/context"))) throw new i("INVALID_CONFIGURATION", "Prompt input cannot use the reserved pretty-aui/context metadata key", { phase: "prompt" });
		if (!n.length || n.every((e) => e.type === "text" && typeof e.text == "string" && !e.text.trim())) throw new i("INVALID_CONFIGURATION", "A prompt cannot be empty", { phase: "prompt" });
		h(n, this.#U().initialized.promptCapabilities, this.#U().version);
		let r = `turn-${++this.#p}`, a = new AbortController(), o = {
			id: r,
			sessionId: t.sessionId,
			abort: a,
			contextSelection: this.#i,
			cancelled: !1,
			submitted: !1
		};
		t.activeTurn = o, t.timeline.beginTurn(), t.timeline.addUserMessage(n, !0), t.phase = "running", t.stopReason = void 0, t.error = void 0, this.#X(t, !0), this.#re({
			type: "turn_started",
			sessionId: t.sessionId,
			turnId: r
		});
		let s = this.#O(o, n);
		return s.catch(() => void 0), {
			id: r,
			done: s
		};
	}
	async addContext() {
		let e = this.#Z("add");
		if (!e.add) throw new i("METHOD_NOT_AVAILABLE", "The context provider does not support adding context", { phase: "context/add" });
		await this.#Q("context/add", () => e.add());
	}
	async removeContext(e) {
		let t = this.#Z("remove");
		if (!t.remove) throw new i("METHOD_NOT_AVAILABLE", "The context provider does not support removing context", { phase: "context/remove" });
		if (!this.#i.some((t) => t.id === e)) throw new i("INVALID_CONFIGURATION", `Unknown context selection '${e}'`, { phase: "context/remove" });
		await this.#Q("context/remove", () => t.remove(e));
	}
	async cancel(e) {
		let t = this.#K(e), n = t.activeTurn;
		if (!n || n.cancelled || (n.cancelled = !0, n.abort.abort(mn), this.#I(t.sessionId), t.phase = "cancelling", this.#X(t, !0), !n.submitted)) return;
		let r = this.#d;
		if (r) try {
			await r.cancel(t.sessionId);
		} catch (e) {
			throw t.activeTurn === n && (n.cancelled = !1, this.#W(e, t.sessionId)), e;
		}
	}
	async reconnect() {
		this.#B(), await this.#ae("connection/reconnect", () => this.#E(!1));
	}
	async newSession() {
		this.#V();
		try {
			await this.#ae("session/new", async () => {
				let e = this.#U(), t = await e.newSession(this.#e.session);
				this.#se(e);
				let n = this.#q(t);
				this.#J(n);
			});
		} catch (e) {
			throw this.#H(e, "session/new");
		}
	}
	async listSessions(e) {
		let t = this.#T;
		if (t) {
			if (t.cursor === e) return t.operation;
			throw new i("SESSION_BUSY", "Wait for the current session-list request to finish", {
				protocol: this.#d?.version,
				phase: "session/list"
			});
		}
		let n = this.#U(), r = Symbol("session/list"), a = Promise.resolve().then(async () => {
			try {
				let t = await n.listSessions(this.#e.session.cwd, e);
				this.#se(n);
				let r = e && this.#f.sessions ? {
					sessions: pn([...this.#f.sessions.sessions, ...t.sessions]).slice(0, 1e3),
					...t.nextCursor ? { nextCursor: t.nextCursor } : {}
				} : t;
				return this.#f = cn({
					...this.#f,
					sessions: r
				}), this.#te(), r;
			} finally {
				this.#T?.token === r && (this.#T = void 0);
			}
		});
		return this.#T = {
			cursor: e,
			operation: a,
			token: r
		}, a;
	}
	async openSession(e) {
		let t = ++this.#g, n = this.#a.get(e);
		if (n) {
			t === this.#g && this.#J(n);
			return;
		}
		this.#V(), await this.#oe(e, "session/open", async () => this.#A(this.#U(), e, [], t));
	}
	async openChildSession(e) {
		let t = this.#K();
		if (this.#z(t, "session/open-child"), e === t.sessionId) return;
		let n = [...this.#f.sessionTrail, {
			sessionId: t.sessionId,
			...t.sessionTitle ? { title: t.sessionTitle } : {}
		}], r = ++this.#g, i = this.#a.get(e);
		if (i) {
			this.#J(i, n);
			return;
		}
		this.#V(), await this.#oe(e, "session/open-child", async () => this.#A(this.#U(), e, n, r));
	}
	async openAncestorSession(e) {
		this.#z(this.#K(), "session/open-ancestor");
		let t = this.#f.sessionTrail.findIndex((t) => t.sessionId === e);
		if (t < 0) throw new i("INVALID_CONFIGURATION", `Session '${e}' is not an ancestor of the active session`, { phase: "session/open-ancestor" });
		let n = this.#f.sessionTrail.slice(0, t), r = ++this.#g, a = this.#a.get(e);
		if (a) {
			this.#J(a, n);
			return;
		}
		this.#V(), await this.#oe(e, "session/open-ancestor", async () => this.#A(this.#U(), e, n, r));
	}
	async closeSession(e) {
		let t = this.#K(e);
		this.#z(t, "session/close"), await this.#oe(t.sessionId, "session/close", async () => {
			let e = this.#U();
			if (await e.closeSession(t.sessionId), this.#se(e), this.#I(t.sessionId), this.#a.delete(t.sessionId), this.#f.sessionId === t.sessionId) {
				let e = [...this.#a.values()].sort((e, t) => t.lastSelected - e.lastSelected)[0];
				e ? this.#J(e) : this.#Y();
			} else this.#te();
		});
	}
	async deleteSession(e) {
		if (e === this.#f.sessionId) throw new i("INVALID_CONFIGURATION", "The active session cannot be deleted", { phase: "session/delete" });
		let t = this.#a.get(e);
		t && this.#z(t, "session/delete"), await this.#oe(e, "session/delete", async () => {
			let n = this.#U();
			await n.deleteSession(e), this.#se(n), t && (this.#I(e), this.#a.delete(e)), this.#f.sessions && (this.#f = cn({
				...this.#f,
				sessions: {
					...this.#f.sessions,
					sessions: this.#f.sessions.sessions.filter((t) => t.sessionId !== e)
				}
			})), this.#te();
		});
	}
	async setConfigOption(e, t) {
		let n = this.#K();
		this.#z(n, "session/set-config"), await this.#oe(n.sessionId, "session/set-config", async () => {
			let r = this.#U(), i = await r.setConfigOption(n.sessionId, e, t);
			this.#se(r), n.configOptions = i.length ? i : n.configOptions.map((n) => n.id === e ? {
				...n,
				currentValue: t
			} : n), this.#X(n);
		});
	}
	async authenticate(e) {
		if (this.#e.allowAuthentication === !1) throw new i("AUTHENTICATION_DISABLED", "Agent authentication is disabled by the host", { phase: "auth/login" });
		let t = this.#f.authMethods.find((t) => t.id === e);
		if (!t) throw new i("INVALID_CONFIGURATION", `Unknown authentication method '${e}'`);
		await this.#ae("auth/login", async () => {
			let e = this.#U();
			this.#b = "connecting", this.#x = void 0, this.#te();
			try {
				await e.authenticate(t), this.#se(e);
				let n = await e.newSession(this.#e.session);
				this.#se(e), this.#b = "ready";
				let r = this.#q(n);
				this.#J(r);
			} catch (e) {
				throw this.#W(e), e;
			}
		});
	}
	async logout() {
		this.#B(), await this.#ae("auth/logout", async () => {
			let e = this.#U();
			await e.logout(), this.#se(e), this.#I(), this.#a.clear(), this.#b = "auth_required", this.#Y();
		});
	}
	respondPermission(e, t) {
		let n = this.#c.get(e);
		return n ? (this.#c.delete(e), n.resolve(t), this.#F(e, n.sessionId), !0) : !1;
	}
	respondElicitation(e, t) {
		let n = this.#l.get(e);
		return n ? (this.#l.delete(e), n.resolve(t), this.#F(e, n.sessionId), !0) : !1;
	}
	async destroy() {
		if (this.#_) return;
		this.#_ = !0, this.#n?.(), this.#n = void 0, this.#r = void 0, this.#y += 1, this.#s?.abort();
		let e = new i("TURN_INTERRUPTED", "Chat was destroyed before the turn completed", {
			phase: "destroy",
			retryable: !1
		});
		for (let t of this.#a.values()) t.activeTurn?.abort.abort(e);
		this.#I();
		let t = this.#d;
		this.#d = void 0, this.#o.clear(), this.#b = "closed", this.#te(), await t?.close().catch(() => void 0), this.#t.clear();
	}
	onUpdate(e, t) {
		if (this.#_) return;
		let n = this.#o.get(e), r = this.#a.get(e);
		if (!n && !r) {
			this.#re({
				type: "diagnostic",
				sessionId: e,
				code: "UNKNOWN_SESSION_UPDATE",
				message: `Ignored an update for unloaded session '${e}'`
			});
			return;
		}
		let i = (n?.timeline ?? r.timeline).reduce(t, this.#d?.version ?? 1);
		if (n) {
			this.#N(n, i);
			return;
		}
		let a = this.#j(r, i);
		this.#X(r, a);
	}
	onPermission(e, t, n) {
		let r = this.#a.get(e);
		if (this.#_ || !r?.activeTurn || !this.#M()) return Promise.resolve({ outcome: "cancelled" });
		let i = `permission-${++this.#p}`, a = {
			...t,
			id: i
		};
		return new Promise((t) => {
			this.#c.set(i, {
				sessionId: e,
				interaction: a,
				resolve: t
			}), this.#P(a, e);
		});
	}
	onElicitation(e, t, n) {
		if (this.#_ || e !== void 0 && !this.#a.has(e) || t.elicitationId !== void 0 && this.#L(t.elicitationId) !== void 0 || !this.#M()) return Promise.resolve({ action: "cancel" });
		let r = `elicitation-${++this.#p}`, i = {
			...t,
			id: r
		};
		return new Promise((t) => {
			this.#l.set(r, {
				...e === void 0 ? {} : { sessionId: e },
				interaction: i,
				resolve: t
			}), this.#P(i, e);
		});
	}
	onElicitationComplete(e) {
		if (this.#_) return;
		let t = this.#L(e);
		if (!t) return;
		let n = this.#l.get(t);
		n && (this.#l.delete(t), n.resolve({ action: "accept" }), this.#F(t, n.sessionId));
	}
	onProtocol(e, t) {
		let n = this.#d?.version;
		n && this.#re({
			type: "protocol",
			protocolVersion: n,
			method: e,
			raw: t
		});
	}
	onDisconnect() {
		this.#_ || (this.#I(), this.#W(new i("CONNECTION_CLOSED", "The ACP connection closed", {
			protocol: this.#d?.version,
			phase: "connection",
			retryable: !0
		})));
	}
	async #E(e) {
		if (this.#v) return this.#v;
		let t = this.#D(e);
		return this.#v = t, t.then(() => {
			this.#v === t && (this.#v = void 0);
		}, () => {
			this.#v === t && (this.#v = void 0);
		}), t;
	}
	async #D(e) {
		if (this.#_) throw z();
		let n = ++this.#y;
		this.#s?.abort();
		let r = new AbortController();
		this.#s = r, this.#b = "connecting", this.#x = void 0, this.#te();
		let a = this.#d, o = this.#f.sessionId, c = this.#S, l = [...this.#a.values()];
		a && (this.#d = void 0, await a.close().catch(() => void 0), this.#le(n));
		let u;
		try {
			if (u = await Kt({
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
			}), !this.#ce(n)) throw await u.close().catch(() => void 0), z();
			if (this.#d = u, this.#f = cn({
				...this.#f,
				protocolVersion: u.version,
				agentName: u.initialized.agentName,
				authMethods: this.#e.allowAuthentication === !1 ? [] : u.initialized.authMethods,
				capabilities: u.initialized.capabilities
			}), this.#te(), this.#re({
				type: "connected",
				protocolVersion: u.version
			}), e) {
				let e = this.#e.initialSession ?? { type: "new" };
				if (e.type === "none") {
					this.#a.clear(), this.#b = "ready", this.#Y();
					return;
				}
				if (e.type === "open") {
					this.#V(), await this.#A(u, e.sessionId, [], ++this.#g), this.#b = "ready", this.#te();
					return;
				}
				let t = await u.newSession(this.#e.session);
				this.#le(n, u), this.#a.clear(), this.#b = "ready", this.#J(this.#q(t));
				return;
			}
			if (!l.length) {
				this.#b = "ready", this.#Y();
				return;
			}
			if (!u.initialized.capabilities.resumeSession && !u.initialized.capabilities.loadSession) {
				let e = await u.newSession(this.#e.session);
				this.#le(n, u), this.#a.clear(), this.#b = "ready", this.#J(this.#q(e));
				return;
			}
			let i = [...l].sort((e, t) => e.sessionId === o ? -1 : t.sessionId === o ? 1 : t.lastSelected - e.lastSelected);
			for (let e of i) try {
				let t = u.initialized.capabilities.resumeSession ? "none" : "all", r = t === "none" ? e.timeline : new s(), i = {
					sessionId: e.sessionId,
					timeline: r,
					configOptions: e.configOptions,
					commands: e.commands,
					sessionTitle: e.sessionTitle
				};
				this.#o.set(e.sessionId, i);
				let a = await u.openSession(e.sessionId, this.#e.session, t);
				this.#le(n, u);
				let l = this.#q(a, r, i, e.instanceId);
				l.lastSelected = e.lastSelected, l.usage = e.usage, e.sessionId === o && this.#J(l, c);
			} catch (n) {
				if (e.sessionId === o) throw n;
				e.phase = "error", e.error = t(n), this.#a.set(e.sessionId, e);
			} finally {
				this.#o.delete(e.sessionId);
			}
			this.#b = "ready", this.#te();
		} catch (e) {
			if (!this.#ce(n)) throw u && this.#d === u && (this.#d = void 0), await u?.close().catch(() => void 0), z();
			if (e instanceof i && e.code === "AUTHENTICATION_REQUIRED" && u?.initialized.authMethods.length) {
				if (this.#e.allowAuthentication === !1) {
					let t = new i("AUTHENTICATION_DISABLED", "The agent requires authentication disabled by the host", {
						cause: e,
						protocol: u?.version,
						phase: "session/new"
					});
					throw this.#W(t), t;
				}
				throw this.#b = "auth_required", this.#x = void 0, this.#te(), new i("AUTHENTICATION_REQUIRED", "Authentication is required before a session can be created", {
					cause: e,
					protocol: u?.version,
					phase: "session/new"
				});
			}
			throw this.#W(e), e;
		}
	}
	async #O(e, t) {
		try {
			let n = this.#U(), r = this.#K(e.sessionId), a = await this.#k(r.sessionId, t, e.contextSelection, e.abort.signal);
			hn(e.abort.signal);
			let o = a.map((e) => ({
				...e,
				content: e.content.map((t) => un(t, e))
			})), s = [...o.flatMap((e) => e.content), ...t];
			if (h(s, n.initialized.promptCapabilities, n.version), !en({
				jsonrpc: "2.0",
				id: 2 ** 53 - 1,
				method: "session/prompt",
				params: {
					sessionId: r.sessionId,
					prompt: s
				}
			})) throw new i("INVALID_CONFIGURATION", "The prepared ACP prompt exceeds the 2 MiB wire-message limit", {
				protocol: n.version,
				phase: "prompt"
			});
			hn(e.abort.signal), e.submitted = !0;
			let c = await n.prompt(r.sessionId, s, () => {
				this.#_ || (r.timeline.markUserAccepted(o), this.#X(r));
			});
			return this.#ie(e, e.cancelled ? "cancelled" : c);
		} catch (t) {
			if (e.cancelled || t === mn) return this.#ie(e, "cancelled");
			let n = this.#a.get(e.sessionId);
			throw n?.activeTurn === e && (n.activeTurn = void 0), this.#W(t, e.sessionId), t;
		}
	}
	async #k(e, t, n, r) {
		try {
			let i = this.#e.context;
			if (!i) return [];
			let a = on(i) ? await gn(i.resolve({
				sessionId: e,
				input: t,
				selection: n,
				...this.#f.protocolVersion ? { protocolVersion: this.#f.protocolVersion } : {},
				capabilities: this.#U().initialized.promptCapabilities,
				signal: r
			}), r) : i;
			if (on(i) && (a.length !== n.length || a.some((e, t) => e.id !== n[t]?.id))) throw Error("Resolved context IDs must match the frozen selection order");
			let o = /* @__PURE__ */ new Set();
			if (a.length > 64) throw Error("Context is limited to 64 items per turn");
			for (let e of a) {
				if (!c(e) || typeof e.id != "string" || !e.id.trim() || e.id.length > 16384) throw Error("Context item IDs must be non-empty bounded strings");
				if (o.has(e.id)) throw Error(`Context item IDs must be unique: '${e.id}'`);
				if (typeof e.label != "string" || !e.label.trim() || e.label.length > 16384) throw Error("Context item labels must be non-empty bounded strings");
				if (!Array.isArray(e.content) || !e.content.length) throw Error("Context items must contain at least one content block");
				o.add(e.id);
			}
			let s = a.map((e) => ({
				id: e.id,
				label: e.label,
				content: e.content.map(dn)
			})), l = this.#U();
			return h(s.flatMap((e) => e.content), l.initialized.promptCapabilities, l.version), s;
		} catch (e) {
			throw r.aborted ? r.reason ?? e : new i("CONTEXT_FAILED", "Context could not be prepared; the prompt was not sent", {
				cause: e,
				protocol: this.#d?.version,
				phase: "context",
				retryable: !0
			});
		}
	}
	async #A(e, t, n, r) {
		let i = {
			sessionId: t,
			timeline: new s(),
			configOptions: [],
			commands: [],
			sessionTitle: void 0
		};
		this.#o.set(t, i);
		try {
			let a = await e.openSession(t, this.#e.session, "all");
			this.#se(e);
			let o = this.#q(a, i.timeline, i);
			r === this.#g ? this.#J(o, n) : this.#te();
		} finally {
			this.#o.get(t) === i && this.#o.delete(t);
		}
	}
	#j(e, t) {
		let n = !1;
		return t.state && !e.activeTurn && (e.phase !== "cancelling" || t.state !== "idle") ? this.#re({
			type: "diagnostic",
			sessionId: e.sessionId,
			code: "STALE_SESSION_STATE",
			message: `Ignored ${t.state} state without an active turn`
		}) : (t.state === "running" && (e.phase = "running", n = !0), t.state === "requires_action" && (e.phase = "awaiting_user", n = !0), t.state === "idle" && (e.phase = "idle", t.stopReason && (e.stopReason = t.stopReason), n = !0)), t.commands && (e.commands = t.commands), t.configOptions && (e.configOptions = t.configOptions), t.sessionTitle !== void 0 && (e.sessionTitle = t.sessionTitle ?? void 0, n = !0), t.usage && (e.usage = t.usage), t.unsupported && this.#re({
			type: "diagnostic",
			sessionId: e.sessionId,
			code: "UNSUPPORTED_UPDATE",
			message: t.unsupported
		}), n;
	}
	#M() {
		return this.#c.size + this.#l.size < 16 || (this.#re({
			type: "diagnostic",
			code: "INTERACTION_LIMIT",
			message: "Cancelled an interaction beyond the 16-interaction limit"
		}), !1);
	}
	#N(e, t) {
		t.commands && (e.commands = t.commands), t.configOptions && (e.configOptions = t.configOptions), t.sessionTitle !== void 0 && (e.sessionTitle = t.sessionTitle ?? void 0);
	}
	#P(e, t) {
		if (t === void 0) {
			this.#u = [...this.#u, e], this.#te();
			return;
		}
		let n = this.#a.get(t);
		n && (n.interactions = [...n.interactions, e], n.phase = "awaiting_user", this.#X(n, !0));
	}
	#F(e, t) {
		if (t === void 0) {
			this.#u = this.#u.filter((t) => t.id !== e), this.#te();
			return;
		}
		let n = this.#a.get(t);
		n && (n.interactions = n.interactions.filter((t) => t.id !== e), n.phase = n.interactions.length ? "awaiting_user" : n.activeTurn ? "running" : "idle", this.#X(n, !0));
	}
	#I(e) {
		for (let [t, n] of this.#c) (e === void 0 || n.sessionId === e) && (this.#c.delete(t), n.resolve({ outcome: "cancelled" }));
		for (let [t, n] of this.#l) (e === void 0 || n.sessionId === e) && (this.#l.delete(t), n.resolve({ action: "cancel" }));
		if (e === void 0) {
			this.#u = [];
			for (let e of this.#a.values()) e.interactions = [], e.activeTurn || (e.phase = "idle");
			this.#te();
			return;
		}
		let t = this.#a.get(e);
		t && (t.interactions = [], t.phase = t.activeTurn ? "running" : "idle", this.#X(t, !0));
	}
	#L(e) {
		for (let [t, n] of this.#l) if (n.interaction.type === "elicitation" && n.interaction.elicitationId === e) return t;
	}
	#R() {
		if (this.#_) throw new i("CONNECTION_CLOSED", "Chat has been destroyed");
		if (this.#b !== "ready" || !this.#d || !this.#f.sessionId) throw new i("SESSION_NOT_READY", "The chat session is not ready", { phase: "prompt" });
		if (this.#f.phase === "auth_required") throw new i("SESSION_NOT_READY", "Authenticate before sending a prompt", { phase: "prompt" });
	}
	#z(e, t) {
		if (e.activeTurn || e.interactions.length) throw new i("SESSION_BUSY", `Finish session '${e.sessionId}' before changing it`, { phase: t });
	}
	#B() {
		if (this.#_) throw z();
		if (this.#u.length || [...this.#a.values()].some((e) => e.activeTurn || e.interactions.length)) throw new i("SESSION_BUSY", "Finish all turns and interactions before replacing the connection", { phase: "connection/reconnect" });
	}
	#V() {
		let e = [...this.#o.keys()].filter((e) => !this.#a.has(e)).length;
		if (!(this.#a.size + e < 16)) throw new i("SESSION_LIMIT", "Close a loaded session before opening another one", { phase: "session" });
	}
	#H(e, t) {
		if (!(e instanceof i) || e.code !== "AUTHENTICATION_REQUIRED" || !this.#d?.initialized.authMethods.length) return e;
		if (this.#e.allowAuthentication === !1) {
			let n = new i("AUTHENTICATION_DISABLED", "The agent requires authentication disabled by the host", {
				cause: e,
				protocol: this.#d.version,
				phase: t
			});
			return this.#W(n), n;
		}
		return this.#b = "auth_required", this.#x = void 0, this.#te(), new i("AUTHENTICATION_REQUIRED", "Authentication is required before a session can be created", {
			cause: e,
			protocol: this.#d.version,
			phase: t
		});
	}
	#U() {
		if (this.#_) throw z();
		if (!this.#d) throw new i("SESSION_NOT_READY", "The ACP connection is not ready");
		return this.#d;
	}
	#W(e, n) {
		if (this.#_) return;
		let r = t(e), i = n ? this.#a.get(n) : void 0;
		if (i) {
			i.phase = "error", i.error = r, this.#X(i, !0), this.#re({
				type: "error",
				sessionId: i.sessionId,
				error: r
			});
			return;
		}
		this.#b = "error", this.#x = r, this.#te(), this.#re({
			type: "error",
			error: r
		});
	}
	#G() {
		let e = this.#f.sessionId;
		return e ? this.#a.get(e) : void 0;
	}
	#K(e = this.#f.sessionId) {
		if (!e) throw new i("SESSION_NOT_READY", "No active session", { phase: "session" });
		let t = this.#a.get(e);
		if (!t) throw new i("SESSION_NOT_READY", `Session '${e}' is not loaded`, { phase: "session" });
		return t;
	}
	#q(e, t = new s(), n, r = `session-instance-${++this.#h}`) {
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
	#J(e, t = []) {
		e.lastSelected = ++this.#m, this.#S = [...t], this.#f = cn({
			...this.#f,
			sessionId: e.sessionId
		}), this.#te(), this.#re({
			type: "session_changed",
			sessionId: e.sessionId
		});
	}
	#Y() {
		this.#S = [], this.#f = cn({
			...this.#f,
			sessionId: void 0
		}), this.#te(), this.#re({ type: "session_changed" });
	}
	#X(e, t = !1) {
		(this.#f.sessionId === e.sessionId || t) && this.#te();
	}
	#Z(e) {
		if (this.#_) throw z();
		let t = this.#e.context;
		if (!on(t)) throw new i("METHOD_NOT_AVAILABLE", "The configured context is not mutable", { phase: `context/${e}` });
		return t;
	}
	async #Q(e, t) {
		if (this.#_) throw z();
		if (this.#r) throw new i("SESSION_BUSY", "Wait for the current context change to finish", { phase: e });
		let n = Symbol(e);
		this.#r = n, this.#te();
		try {
			if (await t(), this.#_ || this.#r !== n) throw z();
			this.#$();
		} catch (t) {
			throw this.#_ ? z() : new i("CONTEXT_FAILED", "Context selection could not be changed", {
				cause: t,
				phase: e,
				retryable: !0
			});
		} finally {
			this.#r === n && (this.#r = void 0, this.#te());
		}
	}
	#$() {
		this.#i = sn(this.#e.context), this.#te();
	}
	#ee() {
		let e = this.#e.context;
		return {
			items: this.#i,
			canAdd: !!(on(e) && e.add),
			canRemove: !!(on(e) && e.remove),
			busy: this.#r !== void 0
		};
	}
	#te() {
		if (this.#_ && this.#b !== "closed") return;
		let e = this.#G(), t = this.#b, n = t === "ready" ? e?.phase ?? "idle" : t, r = t === "error" ? this.#x : e?.error;
		this.#f = cn({
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
			contextSelection: this.#ee(),
			interactions: [...e?.interactions ?? [], ...this.#u],
			authMethods: this.#f.authMethods,
			sessions: this.#f.sessions,
			capabilities: this.#f.capabilities,
			usage: e?.usage,
			stopReason: e?.stopReason,
			error: r,
			phase: n
		}), this.#ne();
	}
	#ne() {
		for (let e of this.#t) try {
			e();
		} catch {}
	}
	#re(e) {
		if (!this.#_) try {
			this.#e.onEvent?.(e);
		} catch {}
	}
	#ie(e, t) {
		if (this.#_) throw z();
		let n = this.#K(e.sessionId);
		return n.activeTurn === e && (n.activeTurn = void 0), n.phase = this.#d?.promptReady(n.sessionId) ? "idle" : "cancelling", n.stopReason = t, this.#X(n, !0), this.#re({
			type: "turn_completed",
			sessionId: n.sessionId,
			turnId: e.id,
			stopReason: t
		}), { stopReason: t };
	}
	async #ae(e, t) {
		if (this.#_) throw z();
		if (this.#C) throw new i("SESSION_BUSY", "Wait for the current connection-level session operation to finish", {
			protocol: this.#d?.version,
			phase: e
		});
		if (this.#w.size) throw new i("SESSION_BUSY", "Wait for target-session operations to finish", {
			protocol: this.#d?.version,
			phase: e
		});
		let n = Symbol(e);
		this.#C = n;
		try {
			return await t();
		} finally {
			this.#C === n && (this.#C = void 0);
		}
	}
	async #oe(e, t, n) {
		if (this.#_) throw z();
		if (this.#C) throw new i("SESSION_BUSY", "Wait for the current connection-level session operation to finish", {
			protocol: this.#d?.version,
			phase: t
		});
		if (this.#w.has(e)) throw new i("SESSION_BUSY", `Wait for the current operation on session '${e}'`, {
			protocol: this.#d?.version,
			phase: t
		});
		let r = Symbol(t);
		this.#w.set(e, r);
		try {
			return await n();
		} finally {
			this.#w.get(e) === r && this.#w.delete(e);
		}
	}
	#se(e) {
		if (this.#_ || this.#d !== e) throw z();
	}
	#ce(e) {
		return !this.#_ && this.#y === e;
	}
	#le(e, t) {
		if (!this.#ce(e) || t !== void 0 && this.#d !== t) throw z();
	}
};
function on(e) {
	return !Array.isArray(e) && c(e) && typeof e.getSelection == "function" && typeof e.subscribe == "function" && typeof e.resolve == "function";
}
function sn(e) {
	if (!e) return Object.freeze([]);
	let t = on(e) ? e.getSelection() : e;
	if (!Array.isArray(t)) throw new i("INVALID_CONFIGURATION", "Context selection must be an array", { phase: "context/selection" });
	if (t.length > 64) throw new i("INVALID_CONFIGURATION", "Context is limited to 64 selected items", { phase: "context/selection" });
	let n = /* @__PURE__ */ new Set(), r = t.map((e) => {
		if (!c(e) || typeof e.id != "string" || !e.id.trim() || e.id.length > 16384) throw new i("INVALID_CONFIGURATION", "Context selection IDs must be non-empty bounded strings", { phase: "context/selection" });
		if (n.has(e.id)) throw new i("INVALID_CONFIGURATION", `Context selection IDs must be unique: '${e.id}'`, { phase: "context/selection" });
		if (typeof e.label != "string" || !e.label.trim() || e.label.length > 16384) throw new i("INVALID_CONFIGURATION", "Context selection labels must be non-empty bounded strings", { phase: "context/selection" });
		return n.add(e.id), Object.freeze({
			id: e.id,
			label: e.label
		});
	});
	return Object.freeze(r);
}
function cn(e) {
	let t = { ...e };
	for (let [e, n] of Object.entries(t)) n === void 0 && delete t[e];
	return t;
}
function ln(e) {
	return typeof e == "string" ? [{
		type: "text",
		text: e
	}] : Array.isArray(e) ? [...e] : [e];
}
function un(e, t) {
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
function dn(e) {
	if (!c(e) || typeof e.type != "string" || !e.type) throw Error("Context content blocks require a type");
	if (c(e._meta) && Object.hasOwn(e._meta, "pretty-aui/context")) throw Error("Context blocks cannot use reserved pretty-aui metadata");
	let t = fn(e);
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
					let t = x(e);
					return t ? [t] : [];
				}) } : {}
			};
		case "resource": {
			if (!c(e.resource) || typeof e.resource.uri != "string") throw Error("Context resources require a uri");
			let n = e.resource, r = n.uri, i = x(n._meta);
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
			...x(e) ?? {},
			...t,
			type: e.type
		};
	}
}
function fn(e) {
	let t = x(e._meta), n = c(e.annotations) ? {
		...Array.isArray(e.annotations.audience) ? { audience: e.annotations.audience.filter((e) => e === "user" || e === "assistant") } : {},
		...typeof e.annotations.priority == "number" && Number.isFinite(e.annotations.priority) ? { priority: e.annotations.priority } : {},
		...typeof e.annotations.lastModified == "string" ? { lastModified: e.annotations.lastModified.slice(0, 16384) } : {}
	} : void 0;
	return {
		...n ? { annotations: n } : {},
		...t ? { _meta: t } : {}
	};
}
function pn(e) {
	let t = /* @__PURE__ */ new Set();
	return e.filter((e) => !t.has(e.sessionId) && (t.add(e.sessionId), !0));
}
var mn = Symbol("turn-cancelled");
function hn(e) {
	if (e.aborted) throw e.reason ?? mn;
}
function gn(e, t) {
	return t.aborted ? Promise.reject(t.reason ?? mn) : new Promise((n, r) => {
		let i = () => {
			r(t.reason ?? mn);
		};
		t.addEventListener("abort", i, { once: !0 }), Promise.resolve(e).then((e) => {
			t.removeEventListener("abort", i), n(e);
		}, (e) => {
			t.removeEventListener("abort", i), r(e);
		});
	});
}
function z() {
	return new i("CONNECTION_CLOSED", "Chat ownership ended before the operation completed", {
		phase: "connection",
		retryable: !1
	});
}
//#endregion
//#region node_modules/.pnpm/dompurify@3.4.14/node_modules/dompurify/dist/purify.es.mjs
function _n(e, t) {
	(t == null || t > e.length) && (t = e.length);
	for (var n = 0, r = Array(t); n < t; n++) r[n] = e[n];
	return r;
}
function vn(e) {
	if (Array.isArray(e)) return e;
}
function yn(e, t) {
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
function bn() {
	throw TypeError("Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.");
}
function xn(e, t) {
	return vn(e) || yn(e, t) || Sn(e, t) || bn();
}
function Sn(e, t) {
	if (e) {
		if (typeof e == "string") return _n(e, t);
		var n = {}.toString.call(e).slice(8, -1);
		return n === "Object" && e.constructor && (n = e.constructor.name), n === "Map" || n === "Set" ? Array.from(e) : n === "Arguments" || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n) ? _n(e, t) : void 0;
	}
}
var Cn = Object.entries, wn = Object.setPrototypeOf, Tn = Object.isFrozen, En = Object.getPrototypeOf, Dn = Object.getOwnPropertyDescriptor, B = Object.freeze, V = Object.seal, On = Object.create, kn = typeof Reflect < "u" && Reflect, An = kn.apply, jn = kn.construct;
B ||= function(e) {
	return e;
}, V ||= function(e) {
	return e;
}, An ||= function(e, t) {
	var n = [...arguments].slice(2);
	return e.apply(t, n);
}, jn ||= function(e) {
	return new e(...[...arguments].slice(1));
};
var Mn = W(Array.prototype.forEach), Nn = W(Array.prototype.lastIndexOf), Pn = W(Array.prototype.pop), Fn = W(Array.prototype.push), In = W(Array.prototype.splice), Ln = Array.isArray, Rn = W(String.prototype.toLowerCase), zn = W(String.prototype.toString), Bn = W(String.prototype.match), Vn = W(String.prototype.replace), Hn = W(String.prototype.indexOf), Un = W(String.prototype.trim), Wn = W(Number.prototype.toString), Gn = W(Boolean.prototype.toString), Kn = typeof BigInt > "u" ? null : W(BigInt.prototype.toString), qn = typeof Symbol > "u" ? null : W(Symbol.prototype.toString), H = W(Object.prototype.hasOwnProperty), Jn = W(Object.prototype.toString), U = W(RegExp.prototype.test), Yn = Xn(TypeError);
function W(e) {
	return function(t) {
		t instanceof RegExp && (t.lastIndex = 0);
		var n = [...arguments].slice(1);
		return An(e, t, n);
	};
}
function Xn(e) {
	return function() {
		return jn(e, [...arguments]);
	};
}
function G(e, t) {
	let n = arguments.length > 2 && arguments[2] !== void 0 ? arguments[2] : Rn;
	if (wn && wn(e, null), !Ln(t)) return e;
	let r = t.length;
	for (; r--;) {
		let i = t[r];
		if (typeof i == "string") {
			let e = n(i);
			e !== i && (Tn(t) || (t[r] = e), i = e);
		}
		e[i] = !0;
	}
	return e;
}
function Zn(e) {
	for (let t = 0; t < e.length; t++) H(e, t) || (e[t] = null);
	return e;
}
function K(e) {
	let t = On(null);
	for (let r of Cn(e)) {
		var n = xn(r, 2);
		let i = n[0], a = n[1];
		H(e, i) && (t[i] = Ln(a) ? Zn(a) : a && typeof a == "object" && a.constructor === Object ? K(a) : a);
	}
	return t;
}
function Qn(e) {
	switch (typeof e) {
		case "string": return e;
		case "number": return Wn(e);
		case "boolean": return Gn(e);
		case "bigint": return Kn ? Kn(e) : "0";
		case "symbol": return qn ? qn(e) : "Symbol()";
		case "undefined": return Jn(e);
		case "function":
		case "object": {
			if (e === null) return Jn(e);
			let t = e, n = q(t, "toString");
			if (typeof n == "function") {
				let e = n(t);
				return typeof e == "string" ? e : Jn(e);
			}
			return Jn(e);
		}
		default: return Jn(e);
	}
}
function q(e, t) {
	for (; e !== null;) {
		let n = Dn(e, t);
		if (n) {
			if (n.get) return W(n.get);
			if (typeof n.value == "function") return W(n.value);
		}
		e = En(e);
	}
	function n() {
		return null;
	}
	return n;
}
function $n(e) {
	try {
		return U(e, ""), !0;
	} catch {
		return !1;
	}
}
var er = B(/* @__PURE__ */ "a.abbr.acronym.address.area.article.aside.audio.b.bdi.bdo.big.blink.blockquote.body.br.button.canvas.caption.center.cite.code.col.colgroup.content.data.datalist.dd.decorator.del.details.dfn.dialog.dir.div.dl.dt.element.em.fieldset.figcaption.figure.font.footer.form.h1.h2.h3.h4.h5.h6.head.header.hgroup.hr.html.i.img.input.ins.kbd.label.legend.li.main.map.mark.marquee.menu.menuitem.meter.nav.nobr.ol.optgroup.option.output.p.picture.pre.progress.q.rp.rt.ruby.s.samp.search.section.select.shadow.slot.small.source.spacer.span.strike.strong.style.sub.summary.sup.table.tbody.td.template.textarea.tfoot.th.thead.time.tr.track.tt.u.ul.var.video.wbr".split(".")), tr = B(/* @__PURE__ */ "svg.a.altglyph.altglyphdef.altglyphitem.animatecolor.animatemotion.animatetransform.circle.clippath.defs.desc.ellipse.enterkeyhint.exportparts.filter.font.g.glyph.glyphref.hkern.image.inputmode.line.lineargradient.marker.mask.metadata.mpath.part.path.pattern.polygon.polyline.radialgradient.rect.stop.style.switch.symbol.text.textpath.title.tref.tspan.view.vkern".split(".")), nr = B([
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
]), rr = B([
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
]), ir = B(/* @__PURE__ */ "math.menclose.merror.mfenced.mfrac.mglyph.mi.mlabeledtr.mmultiscripts.mn.mo.mover.mpadded.mphantom.mroot.mrow.ms.mspace.msqrt.mstyle.msub.msup.msubsup.mtable.mtd.mtext.mtr.munder.munderover.mprescripts".split(".")), ar = B([
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
]), or = B(["#text"]), sr = B(/* @__PURE__ */ "accept.action.align.alt.autocapitalize.autocomplete.autopictureinpicture.autoplay.background.bgcolor.border.capture.cellpadding.cellspacing.checked.cite.class.clear.color.cols.colspan.command.commandfor.controls.controlslist.coords.crossorigin.datetime.decoding.default.dir.disabled.disablepictureinpicture.disableremoteplayback.download.draggable.enctype.enterkeyhint.exportparts.face.for.headers.height.hidden.high.href.hreflang.id.inert.inputmode.integrity.ismap.kind.label.lang.list.loading.loop.low.max.maxlength.media.method.min.minlength.multiple.muted.name.nonce.noshade.novalidate.nowrap.open.optimum.part.pattern.placeholder.playsinline.popover.popovertarget.popovertargetaction.poster.preload.pubdate.radiogroup.readonly.rel.required.rev.reversed.role.rows.rowspan.spellcheck.scope.selected.shape.size.sizes.slot.span.srclang.start.src.srcset.step.style.summary.tabindex.title.translate.type.usemap.valign.value.width.wrap.xmlns".split(".")), cr = B(/* @__PURE__ */ "accent-height.accumulate.additive.alignment-baseline.amplitude.ascent.attributename.attributetype.azimuth.basefrequency.baseline-shift.begin.bias.by.class.clip.clippathunits.clip-path.clip-rule.color.color-interpolation.color-interpolation-filters.color-profile.color-rendering.cx.cy.d.dx.dy.diffuseconstant.direction.display.divisor.dominant-baseline.dur.edgemode.elevation.end.exponent.fill.fill-opacity.fill-rule.filter.filterunits.flood-color.flood-opacity.font-family.font-size.font-size-adjust.font-stretch.font-style.font-variant.font-weight.fx.fy.g1.g2.glyph-name.glyphref.gradientunits.gradienttransform.height.href.id.image-rendering.in.in2.intercept.k.k1.k2.k3.k4.kerning.keypoints.keysplines.keytimes.lang.lengthadjust.letter-spacing.kernelmatrix.kernelunitlength.lighting-color.local.marker-end.marker-mid.marker-start.markerheight.markerunits.markerwidth.maskcontentunits.maskunits.max.mask.mask-type.media.method.mode.min.name.numoctaves.offset.operator.opacity.order.orient.orientation.origin.overflow.paint-order.path.pathlength.patterncontentunits.patterntransform.patternunits.pointer-events.points.preservealpha.preserveaspectratio.primitiveunits.r.rx.ry.radius.refx.refy.repeatcount.repeatdur.restart.result.rotate.scale.seed.shape-rendering.slope.specularconstant.specularexponent.spreadmethod.startoffset.stddeviation.stitchtiles.stop-color.stop-opacity.stroke-dasharray.stroke-dashoffset.stroke-linecap.stroke-linejoin.stroke-miterlimit.stroke-opacity.stroke.stroke-width.style.surfacescale.systemlanguage.tabindex.tablevalues.targetx.targety.transform.transform-origin.text-anchor.text-decoration.text-orientation.text-rendering.textlength.type.u1.u2.unicode.values.vector-effect.viewbox.visibility.version.vert-adv-y.vert-origin-x.vert-origin-y.width.word-spacing.wrap.writing-mode.xchannelselector.ychannelselector.x.x1.x2.xmlns.y.y1.y2.z.zoomandpan".split(".")), lr = B(/* @__PURE__ */ "accent.accentunder.align.bevelled.close.columnalign.columnlines.columnspacing.columnspan.denomalign.depth.dir.display.displaystyle.encoding.fence.frame.height.href.id.largeop.length.linethickness.lquote.lspace.mathbackground.mathcolor.mathsize.mathvariant.maxsize.minsize.movablelimits.notation.numalign.open.rowalign.rowlines.rowspacing.rowspan.rspace.rquote.scriptlevel.scriptminsize.scriptsizemultiplier.selection.separator.separators.stretchy.subscriptshift.supscriptshift.symmetric.voffset.width.xmlns".split(".")), ur = B([
	"xlink:href",
	"xml:id",
	"xlink:title",
	"xml:space",
	"xmlns:xlink"
]), dr = V(/{{[\w\W]*|^[\w\W]*}}/g), fr = V(/<%[\w\W]*|^[\w\W]*%>/g), pr = V(/\${[\w\W]*/g), mr = V(/^data-[\-\w.\u00B7-\uFFFF]+$/), hr = V(/^aria-[\-\w]+$/), gr = V(/^(?:(?:(?:f|ht)tps?|mailto|tel|callto|sms|cid|xmpp|matrix):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i), _r = V(/^(?:\w+script|data):/i), vr = V(/[\u0000-\u0020\u00A0\u1680\u180E\u2000-\u2029\u205F\u3000]/g), yr = V(/^html$/i), br = V(/^[a-z][.\w]*(-[.\w]+)+$/i), xr = V(/<[/\w!]/g), Sr = V(/<[/\w]/g), Cr = V(/<\/no(script|embed|frames)/i), wr = V(/\/>/i), J = {
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
}, Tr = [
	"style",
	"script",
	"xmp",
	"iframe",
	"noembed",
	"noframes",
	"plaintext",
	"noscript"
], Er = B(G({}, Tr)), Dr = function() {
	let e = {};
	return Mn(Tr, (t) => {
		e[t] = V(RegExp("</" + t + "(?=[\\t\\n\\f\\r />])", "i"));
	}), B(e);
}(), Or = function() {
	return typeof window > "u" ? null : window;
}, kr = function(e, t) {
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
}, Ar = function() {
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
}, jr = function(e, t, n, r) {
	return H(e, t) && Ln(e[t]) ? G(r.base ? K(r.base) : {}, e[t], r.transform) : n;
}, Mr = function(e, t, n) {
	let r = H(e, t) ? e[t] : void 0;
	return r && typeof r == "object" ? K(r) : n();
};
function Nr() {
	let e = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : Or(), t = (e) => Nr(e);
	if (t.version = "3.4.14", t.removed = [], !e || !e.document || e.document.nodeType !== J.document || !e.Element) return t.isSupported = !1, t;
	let n = e.document, r = n, i = r.currentScript;
	e.DocumentFragment;
	let a = e.HTMLTemplateElement, o = e.Node, s = e.Element, c = e.NodeFilter;
	e.NamedNodeMap === void 0 && (e.NamedNodeMap || e.MozNamedAttrMap), e.HTMLFormElement;
	let l = e.DOMParser, u = e.trustedTypes, d = s.prototype, f = q(d, "cloneNode"), p = q(d, "remove"), m = q(d, "nextSibling"), h = q(d, "childNodes"), g = q(d, "parentNode"), _ = q(d, "shadowRoot"), v = q(d, "attributes"), y = o && o.prototype ? q(o.prototype, "nodeType") : null, b = o && o.prototype ? q(o.prototype, "nodeName") : null, x = o && o.prototype ? q(o.prototype, "ownerDocument") : null, S = function(e) {
		return y ? y(e) : e.nodeType;
	}, ee = function(e) {
		return b ? b(e) : e.nodeName;
	};
	if (typeof a == "function") {
		let e = n.createElement("template");
		e.content && e.content.ownerDocument && (n = e.content.ownerDocument);
	}
	let C, w = "", te, T = !1, ne = 0, re = function() {
		if (ne > 0) throw Yn("A configured TRUSTED_TYPES_POLICY callback (createHTML or createScriptURL) must not call DOMPurify.sanitize, as that causes infinite recursion. Do not pass a policy whose callbacks wrap DOMPurify as TRUSTED_TYPES_POLICY; see the \"DOMPurify and Trusted Types\" section of the README.");
	}, ie = function(e) {
		re(), ne++;
		try {
			return C.createHTML(e);
		} finally {
			ne--;
		}
	}, ae = function(e) {
		re(), ne++;
		try {
			return C.createScriptURL(e);
		} finally {
			ne--;
		}
	}, oe = function() {
		return T ||= (te = kr(u, i), !0), te;
	}, se = n, ce = se.implementation, le = se.createNodeIterator, ue = se.createDocumentFragment, de = se.getElementsByTagName, fe = r.importNode, E = Ar();
	t.isSupported = typeof Cn == "function" && typeof g == "function" && ce && ce.createHTMLDocument !== void 0;
	let pe = dr, me = fr, he = pr, ge = mr, _e = hr, ve = _r, ye = vr, D = br, O = gr, k = null, be = G({}, [
		...er,
		...tr,
		...nr,
		...ir,
		...or
	]), A = null, xe = G({}, [
		...sr,
		...cr,
		...lr,
		...ur
	]), j = Object.seal(On(null, {
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
	})), Se = null, Ce = null, we = Object.seal(On(null, {
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
	})), Te = !0, Ee = !0, De = !1, Oe = !0, ke = !1, Ae = !0, je = !1, Me = !1, Ne = null, Pe = null, Fe = !1, Ie = !1, Le = !1, Re = !1, ze = !0, Be = !1, M = "user-content-", Ve = !0, He = !1, Ue = {}, We = null, N = G({}, /* @__PURE__ */ "annotation-xml.audio.colgroup.desc.foreignobject.head.iframe.math.mi.mn.mo.ms.mtext.noembed.noframes.noscript.plaintext.script.selectedcontent.style.svg.template.thead.title.video.xmp".split(".")), Ge = null, Ke = G({}, [
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
	]), Ye = "http://www.w3.org/1998/Math/MathML", Xe = "http://www.w3.org/2000/svg", P = "http://www.w3.org/1999/xhtml", F = P, Ze = !1, I = null, Qe = G({}, [
		Ye,
		Xe,
		P
	], zn), L = B([
		"mi",
		"mo",
		"mn",
		"ms",
		"mtext"
	]), $e = G({}, L), et = B(["annotation-xml"]), tt = G({}, et), nt = G({}, [
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
		(!e || typeof e != "object") && (e = {}), e = K(e), rt = it.indexOf(e.PARSER_MEDIA_TYPE) === -1 ? "text/html" : e.PARSER_MEDIA_TYPE, R = rt === "application/xhtml+xml" ? zn : Rn, k = jr(e, "ALLOWED_TAGS", be, { transform: R }), A = jr(e, "ALLOWED_ATTR", xe, { transform: R }), I = jr(e, "ALLOWED_NAMESPACES", Qe, { transform: zn }), qe = jr(e, "ADD_URI_SAFE_ATTR", Je, {
			transform: R,
			base: Je
		}), Ge = jr(e, "ADD_DATA_URI_TAGS", Ke, {
			transform: R,
			base: Ke
		}), We = jr(e, "FORBID_CONTENTS", N, { transform: R }), Se = jr(e, "FORBID_TAGS", K({}), { transform: R }), Ce = jr(e, "FORBID_ATTR", K({}), { transform: R }), Ue = H(e, "USE_PROFILES") ? e.USE_PROFILES && typeof e.USE_PROFILES == "object" ? K(e.USE_PROFILES) : e.USE_PROFILES : !1, Te = e.ALLOW_ARIA_ATTR !== !1, Ee = e.ALLOW_DATA_ATTR !== !1, De = e.ALLOW_UNKNOWN_PROTOCOLS || !1, Oe = e.ALLOW_SELF_CLOSE_IN_ATTR !== !1, ke = e.SAFE_FOR_TEMPLATES || !1, Ae = e.SAFE_FOR_XML !== !1, je = e.WHOLE_DOCUMENT || !1, Ie = e.RETURN_DOM || !1, Le = e.RETURN_DOM_FRAGMENT || !1, Re = e.RETURN_TRUSTED_TYPE || !1, Fe = e.FORCE_BODY || !1, ze = e.SANITIZE_DOM !== !1, Be = e.SANITIZE_NAMED_PROPS || !1, Ve = e.KEEP_CONTENT !== !1, He = e.IN_PLACE || !1, O = $n(e.ALLOWED_URI_REGEXP) ? e.ALLOWED_URI_REGEXP : gr, F = typeof e.NAMESPACE == "string" ? e.NAMESPACE : P, $e = Mr(e, "MATHML_TEXT_INTEGRATION_POINTS", () => G({}, L)), tt = Mr(e, "HTML_INTEGRATION_POINTS", () => G({}, et));
		let t = Mr(e, "CUSTOM_ELEMENT_HANDLING", () => On(null));
		if (j = On(null), H(t, "tagNameCheck") && st(t.tagNameCheck) && (j.tagNameCheck = t.tagNameCheck), H(t, "attributeNameCheck") && st(t.attributeNameCheck) && (j.attributeNameCheck = t.attributeNameCheck), H(t, "allowCustomizedBuiltInElements") && typeof t.allowCustomizedBuiltInElements == "boolean" && (j.allowCustomizedBuiltInElements = t.allowCustomizedBuiltInElements), V(j), ke && (Ee = !1), Le && (Ie = !0), Ue && (k = G({}, or), A = On(null), Ue.html === !0 && (G(k, er), G(A, sr)), Ue.svg === !0 && (G(k, tr), G(A, cr), G(A, ur)), Ue.svgFilters === !0 && (G(k, nr), G(A, cr), G(A, ur)), Ue.mathMl === !0 && (G(k, ir), G(A, lr), G(A, ur))), we.tagCheck = null, we.attributeCheck = null, H(e, "ADD_TAGS") && (typeof e.ADD_TAGS == "function" ? we.tagCheck = e.ADD_TAGS : Ln(e.ADD_TAGS) && (k === be && (k = K(k)), G(k, e.ADD_TAGS, R))), H(e, "ADD_ATTR") && (typeof e.ADD_ATTR == "function" ? we.attributeCheck = e.ADD_ATTR : Ln(e.ADD_ATTR) && (A === xe && (A = K(A)), G(A, e.ADD_ATTR, R))), H(e, "ADD_FORBID_CONTENTS") && Ln(e.ADD_FORBID_CONTENTS) && (We === N && (We = K(We)), G(We, e.ADD_FORBID_CONTENTS, R)), Ve && (k["#text"] = !0), je && G(k, [
			"html",
			"head",
			"body"
		]), k.table && (G(k, ["tbody"]), delete Se.tbody), e.TRUSTED_TYPES_POLICY) {
			if (typeof e.TRUSTED_TYPES_POLICY.createHTML != "function") throw Yn("TRUSTED_TYPES_POLICY configuration option must provide a \"createHTML\" hook.");
			if (typeof e.TRUSTED_TYPES_POLICY.createScriptURL != "function") throw Yn("TRUSTED_TYPES_POLICY configuration option must provide a \"createScriptURL\" hook.");
			let t = C;
			C = e.TRUSTED_TYPES_POLICY;
			try {
				w = ie("");
			} catch (e) {
				throw C = t, e;
			}
		} else e.TRUSTED_TYPES_POLICY === null ? (C = void 0, w = "") : (C === void 0 && (C = oe()), C && typeof w == "string" && (w = ie("")));
		B && B(e), at = e;
	}, lt = G({}, [
		...tr,
		...nr,
		...rr
	]), ut = G({}, [...ir, ...ar]), dt = function(e, t, n) {
		return t.namespaceURI === P ? e === "svg" : t.namespaceURI === Ye ? e === "svg" && (n === "annotation-xml" || $e[n]) : !!lt[e];
	}, ft = function(e, t, n) {
		return t.namespaceURI === P ? e === "math" : t.namespaceURI === Xe ? e === "math" && tt[n] : !!ut[e];
	}, pt = function(e, t, n) {
		return t.namespaceURI === Xe && !tt[n] || t.namespaceURI === Ye && !$e[n] ? !1 : !ut[e] && (nt[e] || !lt[e]);
	}, mt = function(e) {
		let t = g(e);
		(!t || !t.tagName) && (t = {
			namespaceURI: F,
			tagName: "template"
		});
		let n = Rn(e.tagName), r = Rn(t.tagName);
		return I[e.namespaceURI] ? e.namespaceURI === Xe ? dt(n, t, r) : e.namespaceURI === Ye ? ft(n, t, r) : e.namespaceURI === P ? pt(n, t, r) : !!(rt === "application/xhtml+xml" && I[e.namespaceURI]) : !1;
	}, ht = function(e) {
		Fn(t.removed, { element: e });
		try {
			g(e).removeChild(e);
		} catch {
			if (p(e), !g(e)) throw Yn("a node selected for removal could not be detached from its tree and cannot be safely returned; refusing to sanitize in place");
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
			Mn(t, (t) => {
				Fn(e, t);
			}), Mn(e, (e) => {
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
		Fn(t.removed, {
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
			S(e) === J.element && yt(e);
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
			if (n === J.processingInstruction || n === J.comment && U(Sr, e.data)) {
				try {
					p(e);
				} catch {}
				continue;
			}
			if (n === J.element) {
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
			let t = Bn(e, /^[\r\n\t ]+/);
			r = t && t[0];
		}
		rt === "application/xhtml+xml" && F === P && (e = "<html xmlns=\"http://www.w3.org/1999/xhtml\"><head></head><body>" + e + "</body></html>");
		let i = C ? ie(e) : e;
		if (F === P) try {
			t = new l().parseFromString(i, rt);
		} catch {}
		if (!t || !t.documentElement) {
			t = ce.createDocument(F, "template", null);
			try {
				t.documentElement.innerHTML = Ze ? w : i;
			} catch {}
		}
		let a = t.body || t.documentElement;
		return e && r && a.insertBefore(n.createTextNode(r), a.childNodes[0] || null), F === P ? de.call(t, je ? "html" : "body")[0] : je ? t.documentElement : a;
	}, wt = function(e) {
		let t = x ? x(e) : e.ownerDocument;
		return le.call(t || e, e, c.SHOW_ELEMENT | c.SHOW_COMMENT | c.SHOW_TEXT | c.SHOW_PROCESSING_INSTRUCTION | c.SHOW_CDATA_SECTION, null);
	}, Tt = function(e) {
		return e = Vn(e, pe, " "), e = Vn(e, me, " "), e = Vn(e, he, " "), e;
	}, Et = function(e) {
		e.normalize();
		let t = x ? x(e) : e.ownerDocument, n = le.call(t || e, e, c.SHOW_TEXT | c.SHOW_COMMENT | c.SHOW_CDATA_SECTION | c.SHOW_PROCESSING_INSTRUCTION, null), r = n.nextNode();
		for (; r;) r.data = Tt(r.data), r = n.nextNode();
		let i = e.querySelectorAll?.call(e, "template");
		i && Mn(i, (e) => {
			Ot(e.content) && Et(e.content);
		});
	}, Dt = function(e) {
		let t = b ? b(e) : null;
		return typeof t != "string" || R(t) !== "form" ? !1 : typeof e.nodeName != "string" || typeof e.textContent != "string" || typeof e.removeChild != "function" || e.attributes !== v(e) || typeof e.removeAttribute != "function" || typeof e.setAttribute != "function" || typeof e.namespaceURI != "string" || typeof e.insertBefore != "function" || typeof e.hasChildNodes != "function" || e.nodeType !== y(e) || e.childNodes !== h(e);
	}, Ot = function(e) {
		if (!y || typeof e != "object" || !e) return !1;
		try {
			return y(e) === J.documentFragment;
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
		e.length !== 0 && Mn(e, (e) => {
			e.call(t, n, r, at);
		});
	}
	let jt = function(e, t) {
		return !!(Ae && e.hasChildNodes() && !kt(e.firstElementChild) && U(xr, e.textContent) && U(xr, e.innerHTML) || Ae && e.namespaceURI === P && Er[t] && (kt(e.firstElementChild) || typeof e.textContent == "string" && U(Dr[t], e.textContent)) || e.nodeType === J.processingInstruction || Ae && e.nodeType === J.comment && U(Sr, e.data));
	}, Mt = function(e, t) {
		return e instanceof RegExp ? U(e, t) : e instanceof Function && !!e(t, ...[...arguments].slice(2));
	}, Nt = function(e, t, n) {
		if (!Se[t] && zt(t) && Mt(j.tagNameCheck, t)) return !1;
		if (Ve && !We[t]) {
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
		return e === t || g(e) !== null ? !1 : (He && bt(e), !0);
	}, It = function(e, n) {
		if (At(E.beforeSanitizeElements, e, null), Ft(e, n)) return !0;
		if (Dt(e)) return ht(e), !0;
		let r = R(ee(e));
		if (k = Pt(E.uponSanitizeElement, k, be, Ne), At(E.uponSanitizeElement, e, {
			tagName: r,
			allowedTags: k
		}), Ft(e, n)) return !0;
		if (jt(e, r)) return ht(e), !0;
		if (Se[r] || !(we.tagCheck instanceof Function && we.tagCheck(r)) && !k[r]) {
			let t = Nt(e, r, n);
			return t === !1 && At(E.afterSanitizeElements, e, null), t;
		}
		if (S(e) === J.element && !mt(e) || (r === "noscript" || r === "noembed" || r === "noframes") && U(Cr, e.innerHTML)) return ht(e), !0;
		if (ke && e.nodeType === J.text) {
			let n = Tt(e.textContent);
			e.textContent !== n && (Fn(t.removed, { element: e.cloneNode() }), e.textContent = n);
		}
		return At(E.afterSanitizeElements, e, null), !1;
	}, Lt = function(e, t, r) {
		if (Ce[t] || xt(t, e) || ze && (t === "id" || t === "name") && (r in n || r in ot)) return !1;
		let i = A[t] || we.attributeCheck instanceof Function && we.attributeCheck(t, e);
		return Ee && U(ge, t) || Te && U(_e, t) ? !0 : i ? qe[t] || U(O, Vn(r, ye, "")) || (t === "src" || t === "xlink:href" || t === "href") && e !== "script" && Hn(r, "data:") === 0 && Ge[e] || De && !U(ve, Vn(r, ye, "")) ? !0 : !r : zt(e) && Mt(j.tagNameCheck, e) && Mt(j.attributeNameCheck, t, e) || t === "is" && j.allowCustomizedBuiltInElements && Mt(j.tagNameCheck, r);
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
		return !Rt[Rn(e)] && U(D, e);
	}, Bt = function(e, t, n, r) {
		if (C && typeof u == "object" && typeof u.getAttributeType == "function" && !n) switch (u.getAttributeType(e, t)) {
			case "TrustedHTML": return ie(r);
			case "TrustedScriptURL": return ae(r);
		}
		return r;
	}, Vt = function(e, n, r, i) {
		try {
			r ? e.setAttributeNS(r, n, i) : e.setAttribute(n, i), Dt(e) ? ht(e) : Pn(t.removed);
		} catch {
			vt(n, e);
		}
	}, Ht = function(e) {
		At(E.beforeSanitizeAttributes, e, null);
		let t = e.attributes;
		if (!t || Dt(e)) return;
		A = Pt(E.uponSanitizeAttribute, A, xe, Pe);
		let n = {
			attrName: "",
			attrValue: "",
			keepAttr: !0,
			allowedAttributes: A,
			forceKeepAttr: void 0
		}, r = t.length, i = R(e.nodeName);
		for (; r--;) {
			let a = t[r], o = a.name, s = a.namespaceURI, c = a.value, l = R(o), u = c, d = o === "value" ? u : Un(u);
			if (n.attrName = l, n.attrValue = d, n.keepAttr = !0, n.forceKeepAttr = void 0, At(E.uponSanitizeAttribute, e, n), d = n.attrValue, Be && (l === "id" || l === "name") && Hn(d, M) !== 0 && (vt(o, e, a), d = M + d), Ae && U(/((--!?|])>)|<\/(style|script|title|xmp|textarea|noscript|iframe|noembed|noframes)/i, d)) {
				vt(o, e, a);
				continue;
			}
			if (l === "attributename" && Bn(d, "href")) {
				vt(o, e, a);
				continue;
			}
			if (!n.forceKeepAttr) {
				if (!n.keepAttr) {
					vt(o, e, a);
					continue;
				}
				if (!Oe && U(wr, d)) {
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
		At(E.afterSanitizeAttributes, e, null);
	}, Ut = function(e) {
		let t = null, n = wt(e);
		for (At(E.beforeSanitizeShadowDOM, e, null); t = n.nextNode();) if (At(E.uponSanitizeShadowNode, t, null), It(t, e), Ht(t), Ot(t.content) && Ut(t.content), S(t) === J.element) {
			let e = _(t);
			Ot(e) && (Wt(e), Ut(e));
		}
		At(E.afterSanitizeShadowDOM, e, null);
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
			let n = e.node, r = S(n) === J.element, i = h(n);
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
		if (Ze = !e, Ze && (e = "<!-->"), typeof e != "string" && !kt(e) && (e = Qn(e), typeof e != "string")) throw Yn("dirty is not a string, aborting");
		if (!t.isSupported) return e;
		Me ? (k = Ne, A = Pe) : ct(n), (E.uponSanitizeElement.length > 0 || E.uponSanitizeAttribute.length > 0) && (k = K(k)), E.uponSanitizeAttribute.length > 0 && (A = K(A)), t.removed = [];
		let c = He && typeof e != "string" && kt(e);
		if (c) {
			St(e);
			let t = ee(e);
			if (typeof t == "string") {
				let n = R(t);
				if (!k[n] || Se[n]) throw _t(e), Yn("root node is forbidden and cannot be sanitized in-place");
			}
			if (Dt(e)) throw _t(e), Yn("root node is clobbered and cannot be sanitized in-place");
			try {
				Wt(e);
			} catch (t) {
				throw _t(e), t;
			}
		} else if (kt(e)) i = Ct("<!---->"), a = i.ownerDocument.importNode(e, !0), a.nodeType === J.element && a.nodeName === "BODY" || a.nodeName === "HTML" ? i = a : i.appendChild(a), Wt(a);
		else {
			if (!Ie && !ke && !je && e.indexOf("<") === -1) return C && Re ? ie(e) : e;
			if (i = Ct(e), !i) return Ie ? null : Re ? w : "";
		}
		i && Fe && ht(i.firstChild);
		let l = c ? e : i;
		try {
			let e = wt(l);
			for (; o = e.nextNode();) It(o, l), Ht(o), Ot(o.content) && Ut(o.content);
		} catch (n) {
			throw c && (_t(e), Mn(t.removed, (e) => {
				e.element && bt(e.element);
			})), n;
		}
		if (c) return Mn(t.removed, (e) => {
			e.element && bt(e.element);
		}), ke && Et(e), e;
		if (Ie) {
			if (ke && Et(i), Le) for (s = ue.call(i.ownerDocument); i.firstChild;) s.appendChild(i.firstChild);
			else s = i;
			return (A.shadowroot || A.shadowrootmode) && (s = fe.call(r, s, !0)), s;
		}
		let u = je ? i.outerHTML : i.innerHTML;
		return je && k["!doctype"] && i.ownerDocument && i.ownerDocument.doctype && i.ownerDocument.doctype.name && U(yr, i.ownerDocument.doctype.name) && (u = "<!DOCTYPE " + i.ownerDocument.doctype.name + ">\n" + u), ke && (u = Tt(u)), C && Re ? ie(u) : u;
	}, t.setConfig = function() {
		let e = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : {};
		ct(e), Me = !0, Ne = k, Pe = A;
	}, t.clearConfig = function() {
		at = null, Me = !1, Ne = null, Pe = null, C = te, w = "";
	}, t.isValidAttribute = function(e, t, n) {
		at || ct({});
		let r = R(e), i = R(t);
		return Lt(r, i, n);
	}, t.addHook = function(e, t) {
		typeof t == "function" && H(E, e) && Fn(E[e], t);
	}, t.removeHook = function(e, t) {
		if (H(E, e)) {
			if (t !== void 0) {
				let n = Nn(E[e], t);
				return n === -1 ? void 0 : In(E[e], n, 1)[0];
			}
			return Pn(E[e]);
		}
	}, t.removeHooks = function(e) {
		H(E, e) && (E[e] = []);
	}, t.removeAllHooks = function() {
		E = Ar();
	}, t;
}
var Pr = Nr();
//#endregion
//#region node_modules/.pnpm/marked@18.0.10/node_modules/marked/lib/marked.esm.js
function Fr() {
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
var Ir = Fr();
function Lr(e) {
	Ir = e;
}
var Rr = { exec: () => null };
function zr(e) {
	let t = [];
	return (n) => {
		let r = Math.max(0, Math.min(3, n - 1)), i = t[r];
		return i || (i = e(r), t[r] = i), i;
	};
}
function Y(e, t = "") {
	let n = typeof e == "string" ? e : e.source, r = {
		replace: (e, t) => {
			let i = typeof t == "string" ? t : t.source;
			return i = i.replace(X.caret, "$1"), n = n.replace(e, i), r;
		},
		getRegex: () => new RegExp(n, t)
	};
	return r;
}
var Br = ((e = "") => {
	try {
		return !!RegExp("(?<=1)(?<!1)" + e);
	} catch {
		return !1;
	}
})(), X = {
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
	nextBulletRegex: zr((e) => RegExp(`^ {0,${e}}(?:[*+-]|\\d{1,9}[.)])((?:[ 	][^\\n]*)?(?:\\n|$))`)),
	hrRegex: zr((e) => RegExp(`^ {0,${e}}((?:- *){3,}|(?:_ *){3,}|(?:\\* *){3,})(?:\\n+|$)`)),
	fencesBeginRegex: zr((e) => RegExp(`^ {0,${e}}(?:\`\`\`|~~~)`)),
	headingBeginRegex: zr((e) => RegExp(`^ {0,${e}}#`)),
	htmlBeginRegex: zr((e) => RegExp(`^ {0,${e}}<(?:[a-z].*>|!--)`, "i")),
	blockquoteBeginRegex: zr((e) => RegExp(`^ {0,${e}}>`))
}, Vr = /^(?:[ \t]*(?:\n|$))+/, Hr = /^((?: {4}| {0,3}\t)[^\n]+(?:\n(?:[ \t]*(?:\n|$))*)?)+/, Ur = /^ {0,3}(`{3,}(?=[^`\n]*(?:\n|$))|~{3,})([^\n]*)(?:\n|$)(?:|([\s\S]*?)(?:\n|$))(?: {0,3}\1[~`]* *(?=\n|$)|$)/, Wr = /^ {0,3}((?:-[\t ]*){3,}|(?:_[ \t]*){3,}|(?:\*[ \t]*){3,})(?:\n+|$)/, Gr = /^ {0,3}(#{1,6})(?=\s|$)(.*)(?:\n+|$)/, Kr = / {0,3}(?:[*+-]|\d{1,9}[.)])/, qr = /^(?!bull |blockCode|fences|blockquote|heading|html|table)((?:.|\n(?!\s*?\n|bull |blockCode|fences|blockquote|heading|html|table))+?)\n {0,3}(=+|-+) *(?:\n+|$)/, Jr = Y(qr).replace(/bull/g, Kr).replace(/blockCode/g, /(?: {4}| {0,3}\t)/).replace(/fences/g, / {0,3}(?:`{3,}|~{3,})/).replace(/blockquote/g, / {0,3}>/).replace(/heading/g, / {0,3}#{1,6}(?:\s|$)/).replace(/html/g, / {0,3}<[^\n>]+>\n/).replace(/\|table/g, "").getRegex(), Yr = Y(qr).replace(/bull/g, Kr).replace(/blockCode/g, /(?: {4}| {0,3}\t)/).replace(/fences/g, / {0,3}(?:`{3,}|~{3,})/).replace(/blockquote/g, / {0,3}>/).replace(/heading/g, / {0,3}#{1,6}(?:\s|$)/).replace(/html/g, / {0,3}<[^\n>]+>\n/).replace(/table/g, / {0,3}\|?(?:[:\- ]*\|)+[\:\- ]*\n/).getRegex(), Xr = /^([^\n]+(?:\n(?!hr|heading|lheading|blockquote|fences|list|html|table|[ \t]+\n)[^\n]+)*)/, Zr = /^[^\n]+/, Qr = /(?!\s*\])(?:\\[\s\S]|[^\[\]\\])+/, $r = Y(/^ {0,3}\[(label)\]: *(?:\n[ \t]*)?([^<\s][^\s]*|<.*?>)(?:(?: +(?:\n[ \t]*)?| *\n[ \t]*)(title))? *(?:\n+|$)/).replace("label", Qr).replace("title", /(?:"(?:\\"?|[^"\\])*"|'[^'\n]*(?:\n[^'\n]+)*\n?'|\([^()]*\))/).getRegex(), ei = Y(/^(bull)([ \t][^\n]*?)?(?:\n|$)/).replace(/bull/g, Kr).getRegex(), ti = "address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|frameset|h[1-6]|head|header|hr|html|iframe|legend|li|link|main|menu|menuitem|meta|nav|noframes|ol|optgroup|option|p|param|search|section|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul", ni = /<!--(?:-?>|[\s\S]*?(?:-->|$))/, ri = Y("^ {0,3}(?:<(script|pre|style|textarea)[\\s>][\\s\\S]*?(?:</\\1>[^\\n]*\\n*|$)|comment[^\\n]*(\\n+|$)|<\\?[\\s\\S]*?(?:\\?>[^\\n]*\\n*|$)|<![A-Z][\\s\\S]*?(?:>[^\\n]*\\n*|$)|<!\\[CDATA\\[[\\s\\S]*?(?:\\]\\]>[^\\n]*\\n*|$)|</?(tag)(?: +|\\n|/?>)[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$)|<(?!script|pre|style|textarea)([a-z][\\w-]*)(?:attribute)*? */?>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$)|</(?!script|pre|style|textarea)[a-z][\\w-]*\\s*>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$))", "i").replace("comment", ni).replace("tag", ti).replace("attribute", / +[a-zA-Z:_][\w.:-]*(?: *= *"[^"\n]*"| *= *'[^'\n]*'| *= *[^\s"'=<>`]+)?/).getRegex(), ii = (e) => Y(Xr).replace("hr", Wr).replace("heading", " {0,3}#{1,6}(?:\\s|$)").replace("|lheading", "").replace("|table", "").replace("blockquote", " {0,3}>").replace("fences", " {0,3}(?:`{3,}(?=[^`\\n]*(?:\\n|$))|~~~)[^\\n]*(?:\\n|$)").replace("list", e).replace("html", "</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag", ti).getRegex(), ai = ii(/ {0,3}(?:[*+-]|1[.)])[ \t]+[^ \t\n]/), oi = ii(/ {0,3}(?:[*+-]|\d{1,9}[.)])(?:[ \t]|\n|$)/), si = {
	blockquote: Y(/^( {0,3}> ?(paragraph|[^\n]*)(?:\n|$))+/).replace("paragraph", oi).getRegex(),
	code: Hr,
	def: $r,
	fences: Ur,
	heading: Gr,
	hr: Wr,
	html: ri,
	lheading: Jr,
	list: ei,
	newline: Vr,
	paragraph: ai,
	table: Rr,
	text: Zr
}, ci = Y("^ *([^\\n ].*)\\n {0,3}((?:\\| *)?:?-+:? *(?:\\| *:?-+:? *)*(?:\\| *)?)(?:\\n((?:(?! *\\n|hr|heading|blockquote|code|fences|list|html).*(?:\\n|$))*)\\n*|$)").replace("hr", Wr).replace("heading", " {0,3}#{1,6}(?:\\s|$)").replace("blockquote", " {0,3}>").replace("code", "(?: {4}| {0,3}	)[^\\n]").replace("fences", " {0,3}(?:`{3,}(?=[^`\\n]*(?:\\n|$))|~~~)[^\\n]*(?:\\n|$)").replace("list", " {0,3}(?:[*+-]|1[.)])[ \\t]").replace("html", "</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag", ti).getRegex(), li = {
	...si,
	lheading: Yr,
	table: ci,
	paragraph: Y(Xr).replace("hr", Wr).replace("heading", " {0,3}#{1,6}(?:\\s|$)").replace("|lheading", "").replace("table", ci).replace("blockquote", " {0,3}>").replace("fences", " {0,3}(?:`{3,}(?=[^`\\n]*(?:\\n|$))|~~~)[^\\n]*(?:\\n|$)").replace("list", " {0,3}(?:[*+-]|1[.)])[ \\t]+[^ \\t\\n]").replace("html", "</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag", ti).getRegex()
}, ui = {
	...si,
	html: Y("^ *(?:comment *(?:\\n|\\s*$)|<(tag)[\\s\\S]+?</\\1> *(?:\\n{2,}|\\s*$)|<tag(?:\"[^\"]*\"|'[^']*'|\\s[^'\"/>\\s]*)*?/?> *(?:\\n{2,}|\\s*$))").replace("comment", ni).replace(/tag/g, "(?!(?:a|em|strong|small|s|cite|q|dfn|abbr|data|time|code|var|samp|kbd|sub|sup|i|b|u|mark|ruby|rt|rp|bdi|bdo|span|br|wbr|ins|del|img)\\b)\\w+(?!:|[^\\w\\s@]*@)\\b").getRegex(),
	def: /^ *\[([^\]]+)\]: *<?([^\s>]+)>?(?: +(["(][^\n]+[")]))? *(?:\n+|$)/,
	heading: /^(#{1,6})(.*)(?:\n+|$)/,
	fences: Rr,
	lheading: /^(.+?)\n {0,3}(=+|-+) *(?:\n+|$)/,
	paragraph: Y(Xr).replace("hr", Wr).replace("heading", " *#{1,6} *[^\n]").replace("lheading", Jr).replace("|table", "").replace("blockquote", " {0,3}>").replace("|fences", "").replace("|list", "").replace("|html", "").replace("|tag", "").getRegex()
}, di = /^\\([!"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])/, fi = /^(`+)([^`]|[^`][\s\S]*?[^`])\1(?!`)/, pi = /^( {2,}|\\)\n(?!\s*$)/, mi = /^(`+|[^`])(?:(?= {2,}\n)|[\s\S]*?(?:(?=[\\<!\[`*_]|\b_|$)|[^ ](?= {2,}\n)))/, hi = /[\p{P}\p{S}]/u, gi = /[\s\p{P}\p{S}]/u, _i = /[^\s\p{P}\p{S}]/u, vi = Y(/^((?![*_])punctSpace)/, "u").replace(/punctSpace/g, gi).getRegex(), yi = /[\p{Pi}\p{Ps}"']/u, bi = /(?!~)[\p{P}\p{S}]/u, xi = /(?!~)[\s\p{P}\p{S}]/u, Si = /(?:[^\s\p{P}\p{S}]|~)/u, Ci = Y(/link|precode-code|html/, "g").replace("link", /\[(?:[^\[\]`]|(?<a>`+)[^`]+\k<a>(?!`))*?\]\((?:\\[\s\S]|[^\\\(\)]|\((?:\\[\s\S]|[^\\\(\)])*\))*\)/).replace("precode-", Br ? "(?<!`)()" : "(^^|[^`])").replace("code", /(?<b>`+)[^`]+\k<b>(?!`)/).replace("html", /<(?! )[^<>]*?>/).getRegex(), wi = /^(?:\*+(?:((?!\*)punct)|([^\s*]))?)|^_+(?:((?!_)punct)|([^\s_]))?/, Ti = Y(wi, "u").replace(/punct/g, hi).getRegex(), Ei = Y(wi, "u").replace(/punct/g, bi).getRegex(), Di = Y(/^(?:\*+(?:((?!\*)(?!openQuote)punct)|([^\s*]))?)|^_+(?:((?!_)(?!openQuote)punct)|([^\s_]))?/, "u").replace(/openQuote/g, yi).replace(/punct/g, hi).getRegex(), Oi = "^[^_*]*?__[^_*]*?\\*[^_*]*?(?=__)|[^*]+(?=[^*])|(?!\\*)punct(\\*+)(?=[\\s]|$)|notPunctSpace(\\*+)(?!\\*)(?=punctSpace|$)|(?!\\*)punctSpace(\\*+)(?=notPunctSpace)|[\\s](\\*+)(?!\\*)(?=punct)|(?!\\*)punct(\\*+)(?!\\*)(?=punct)|notPunctSpace(\\*+)(?=notPunctSpace)", ki = Y(Oi, "gu").replace(/notPunctSpace/g, _i).replace(/punctSpace/g, gi).replace(/punct/g, hi).getRegex(), Ai = Y(Oi, "gu").replace(/notPunctSpace/g, Si).replace(/punctSpace/g, xi).replace(/punct/g, bi).getRegex(), ji = Y("^[^_*]*?__[^_*]*?\\*[^_*]*?(?=__)|[^*]+(?=[^*])|(?!\\*)punct(\\*+)(?=[\\s]|$)|notPunctSpace(\\*+)(?!\\*)(?=punctSpace|$)|(?!\\*)[\\s](\\*+)(?=notPunctSpace)|[\\s](\\*+)(?!\\*)(?=punct)|(?!\\*)punct(\\*+)(?!\\*)(?=punct)|(?:(?!\\*)punct|notPunctSpace)(\\*+)(?!\\*)(?=notPunctSpace)", "gu").replace(/notPunctSpace/g, _i).replace(/punctSpace/g, gi).replace(/punct/g, hi).getRegex(), Mi = Y("^[^_*]*?\\*\\*[^_*]*?_[^_*]*?(?=\\*\\*)|[^_]+(?=[^_])|(?!_)punct(_+)(?=[\\s]|$)|notPunctSpace(_+)(?!_)(?=punctSpace|$)|(?!_)punctSpace(_+)(?=notPunctSpace)|[\\s](_+)(?!_)(?=punct)|(?!_)punct(_+)(?!_)(?=punct)", "gu").replace(/notPunctSpace/g, _i).replace(/punctSpace/g, gi).replace(/punct/g, hi).getRegex(), Ni = Y("^[^_*]*?\\*\\*[^_*]*?_[^_*]*?(?=\\*\\*)|[^_]+(?=[^_])|(?!_)punct(_+)(?=[\\s]|$)|notPunctSpace(_+)(?!_)(?=punctSpace|$)|(?!_)[\\s](_+)(?=notPunctSpace)|[\\s](_+)(?!_)(?=punct)|(?!_)punct(_+)(?!_)(?=punct)|(?:(?!_)punct|notPunctSpace)(_+)(?!_)(?=notPunctSpace)", "gu").replace(/notPunctSpace/g, _i).replace(/punctSpace/g, gi).replace(/punct/g, hi).getRegex(), Pi = Y(/^~~?(?:((?!~)punct)|[^\s~])/, "u").replace(/punct/g, hi).getRegex(), Fi = Y("^[^~]+(?=[^~])|(?!~)punct(~~?)(?=[\\s]|$)|notPunctSpace(~~?)(?!~)(?=punctSpace|$)|(?!~)punctSpace(~~?)(?=notPunctSpace)|[\\s](~~?)(?!~)(?=punct)|(?!~)punct(~~?)(?!~)(?=punct)|notPunctSpace(~~?)(?=notPunctSpace)", "gu").replace(/notPunctSpace/g, _i).replace(/punctSpace/g, gi).replace(/punct/g, hi).getRegex(), Ii = Y(/\\(punct)/, "gu").replace(/punct/g, hi).getRegex(), Li = Y(/^<(scheme:[^\s\x00-\x1f<>]*|email)>/).replace("scheme", /[a-zA-Z][a-zA-Z0-9+.-]{1,31}/).replace("email", /[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+(@)[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+(?![-_])/).getRegex(), Ri = Y(ni).replace("(?:-->|$)", "-->").getRegex(), zi = Y("^comment|^</[a-zA-Z][\\w:-]*\\s*>|^<[a-zA-Z][\\w-]*(?:attribute)*?\\s*/?>|^<\\?[\\s\\S]*?\\?>|^<![a-zA-Z]+\\s[\\s\\S]*?>|^<!\\[CDATA\\[[\\s\\S]*?\\]\\]>").replace("comment", Ri).replace("attribute", /\s+[a-zA-Z:_][\w.:-]*(?:\s*=\s*"[^"]*"|\s*=\s*'[^']*'|\s*=\s*[^\s"'=<>`]+)?/).getRegex(), Bi = /(?:\[(?:\\[\s\S]|[^\[\]\\])*\]|\\[\s\S]|`+(?!`)[^`]*?`+(?!`)|``+(?=\])|[^\[\]\\`])*?/, Vi = Y(/^!?\[(label)\]\(\s*(href)(?:(?:[ \t]+(?:\n[ \t]*)?|\n[ \t]*)(title))?\s*\)/).replace("label", Bi).replace("href", /<(?:\\.|[^\n<>\\])+>|[^ \t\n\x00-\x1f]+|(?=\))/).replace("title", /"(?:\\"?|[^"\\])*"|'(?:\\'?|[^'\\])*'|\((?:\\\)?|[^)\\])*\)/).getRegex(), Hi = Y(/^!?\[(label)\]\[(ref)\]/).replace("label", Bi).replace("ref", Qr).getRegex(), Ui = Y(/^!?\[(ref)\](?:\[\])?/).replace("ref", Qr).getRegex(), Wi = Y("reflink|nolink(?!\\()", "g").replace("reflink", Hi).replace("nolink", Ui).getRegex(), Gi = /[hH][tT][tT][pP][sS]?|[fF][tT][pP]/, Ki = {
	_backpedal: Rr,
	anyPunctuation: Ii,
	autolink: Li,
	blockSkip: Ci,
	br: pi,
	code: fi,
	del: Rr,
	delLDelim: Rr,
	delRDelim: Rr,
	emStrongLDelim: Ti,
	emStrongRDelimAst: ki,
	emStrongRDelimUnd: Mi,
	escape: di,
	link: Vi,
	nolink: Ui,
	punctuation: vi,
	reflink: Hi,
	reflinkSearch: Wi,
	tag: zi,
	text: mi,
	url: Rr
}, qi = {
	...Ki,
	emStrongLDelim: Di,
	emStrongRDelimAst: ji,
	emStrongRDelimUnd: Ni,
	link: Y(/^!?\[(label)\]\((.*?)\)/).replace("label", Bi).getRegex(),
	reflink: Y(/^!?\[(label)\]\s*\[([^\]]*)\]/).replace("label", Bi).getRegex()
}, Ji = {
	...Ki,
	emStrongRDelimAst: Ai,
	emStrongLDelim: Ei,
	delLDelim: Pi,
	delRDelim: Fi,
	url: Y(/^((?:protocol):\/\/|www\.)(?:[a-zA-Z0-9\-]+\.?)+[^\s<]*|^email/).replace("protocol", Gi).replace("email", /[A-Za-z0-9._+-]+(@)[a-zA-Z0-9-_]+(?:\.[a-zA-Z0-9-_]*[a-zA-Z0-9])+(?![-_])/).getRegex(),
	_backpedal: /(?:[^?!.,:;*_'"~()&]+|\([^)]*\)|&(?![a-zA-Z0-9]+;$)|[?!.,:;*_'"~)]+(?!$))+/,
	del: /^(~~?)(?=[^\s~])((?:\\[\s\S]|[^\\])*?(?:\\[\s\S]|[^\s~\\]))\1(?=[^~]|$)/,
	text: Y(/^(`+|~+|[^`~])(?:(?=[`~])|(?= {2,}\n)|(?=[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@)|[\s\S]*?(?:(?=[\\<!\[`*~_]|\b_|protocol:\/\/|www\.|$)|[^ ](?= {2,}\n)|[^a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-](?=[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@)))/).replace("protocol", Gi).getRegex()
}, Yi = {
	...Ji,
	br: Y(pi).replace("{2,}", "*").getRegex(),
	text: Y(Ji.text).replace("\\b_", "\\b_| {2,}\\n").replace(/\{2,\}/g, "*").getRegex()
}, Xi = {
	normal: si,
	gfm: li,
	pedantic: ui
}, Zi = {
	normal: Ki,
	gfm: Ji,
	breaks: Yi,
	pedantic: qi
}, Qi = {
	"&": "&amp;",
	"<": "&lt;",
	">": "&gt;",
	"\"": "&quot;",
	"'": "&#39;"
}, $i = (e) => Qi[e];
function ea(e, t) {
	if (t) {
		if (X.escapeTest.test(e)) return e.replace(X.escapeReplace, $i);
	} else if (X.escapeTestNoEncode.test(e)) return e.replace(X.escapeReplaceNoEncode, $i);
	return e;
}
function ta(e) {
	try {
		e = encodeURI(e).replace(X.percentDecode, "%");
	} catch {
		return null;
	}
	return e;
}
function na(e, t) {
	let n = e.replace(X.findPipe, (e, t, n) => {
		let r = !1, i = t;
		for (; --i >= 0 && n[i] === "\\";) r = !r;
		return r ? "|" : " |";
	}).split(X.splitPipe), r = 0;
	if (n[0].trim() || n.shift(), n.length > 0 && !n.at(-1)?.trim() && n.pop(), t) {
		if (n.length > t) n.splice(t);
		else for (; n.length < t;) n.push("");
	}
	for (; r < n.length; r++) n[r] = n[r].trim().replace(X.slashPipe, "|");
	return n;
}
function ra(e, t, n) {
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
function ia(e) {
	let t = e.split("\n"), n = t.length - 1;
	for (; n >= 0 && X.blankLine.test(t[n]);) n--;
	return t.length - n <= 2 ? e : t.slice(0, n + 1).join("\n");
}
function aa(e, t) {
	if (e.indexOf(t[1]) === -1) return -1;
	let n = 0;
	for (let r = 0; r < e.length; r++) if (e[r] === "\\") r++;
	else if (e[r] === t[0]) n++;
	else if (e[r] === t[1] && (n--, n < 0)) return r;
	return n > 0 ? -2 : -1;
}
function oa(e, t = 0) {
	let n = t, r = "";
	for (let t of e) if (t === "	") {
		let e = 4 - n % 4;
		r += " ".repeat(e), n += e;
	} else r += t, n++;
	return r;
}
function sa(e, t, n, r, i) {
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
function ca(e, t, n) {
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
var la = class {
	options;
	rules;
	lexer;
	constructor(e) {
		this.options = e || Ir;
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
			let e = this.options.pedantic ? t[0] : ia(t[0]);
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
			let e = t[0], n = ca(e, t[3] || "", this.rules);
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
				let t = ra(e, "#");
				(this.options.pedantic || !t || this.rules.other.endingSpaceChar.test(t)) && (e = t.trim());
			}
			return {
				type: "heading",
				raw: ra(t[0], "\n"),
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
			raw: ra(t[0], "\n")
		};
	}
	blockquote(e) {
		let t = this.rules.block.blockquote.exec(e);
		if (t) {
			let e = ra(t[0], "\n").split("\n"), n = "", r = "", i = [];
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
				let c = oa(t[2].split("\n", 1)[0], t[1].length), l = e.split("\n", 1)[0], u = !c.trim(), d = 0;
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
			let e = ia(t[0]);
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
				raw: ra(t[0], "\n"),
				href: n,
				title: r
			};
		}
	}
	table(e) {
		let t = this.rules.block.table.exec(e);
		if (!t || !this.rules.other.tableDelimiter.test(t[2])) return;
		let n = na(t[1]), r = t[2].replace(this.rules.other.tableAlignChars, "").split("|"), i = t[3]?.trim() ? t[3].replace(this.rules.other.tableRowBlankLine, "").split("\n") : [], a = {
			type: "table",
			raw: ra(t[0], "\n"),
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
			for (let e of i) a.rows.push(na(e, a.header.length).map((e, t) => ({
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
				raw: ra(t[0], "\n"),
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
				let t = ra(e.slice(0, -1), "\\");
				if ((e.length - t.length) % 2 == 0) return;
			} else {
				let e = aa(t[2], "()");
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
			return n = n.trim(), this.rules.other.startAngleBracket.test(n) && (n = this.options.pedantic && !this.rules.other.endAngleBracket.test(e) ? n.slice(1) : n.slice(1, -1)), sa(t, {
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
			return sa(n, e, n[0], this.lexer, this.rules);
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
}, ua = class e {
	tokens;
	options;
	state;
	inlineQueue;
	tokenizer;
	constructor(e) {
		this.tokens = [], this.tokens.links = Object.create(null), this.options = e || Ir, this.options.tokenizer = this.options.tokenizer || new la(), this.tokenizer = this.options.tokenizer, this.tokenizer.options = this.options, this.tokenizer.lexer = this, this.inlineQueue = [], this.state = {
			inLink: !1,
			inRawBlock: !1,
			top: !0
		};
		let t = {
			other: X,
			block: Xi.normal,
			inline: Zi.normal
		};
		this.options.pedantic ? (t.block = Xi.pedantic, t.inline = Zi.pedantic) : this.options.gfm && (t.block = Xi.gfm, t.inline = this.options.breaks ? Zi.breaks : Zi.gfm), this.tokenizer.rules = t;
	}
	static get rules() {
		return {
			block: Xi,
			inline: Zi
		};
	}
	static lex(t, n) {
		return new e(n).lex(t);
	}
	static lexInline(t, n) {
		return new e(n).inlineTokens(t);
	}
	lex(e) {
		e = e.replace(X.carriageReturn, "\n"), this.blockTokens(e, this.tokens);
		for (let e = 0; e < this.inlineQueue.length; e++) {
			let t = this.inlineQueue[e];
			this.inlineTokens(t.src, t.tokens);
		}
		return this.inlineQueue = [], this.tokens;
	}
	blockTokens(e, t = [], n = !1) {
		this.tokenizer.lexer = this, this.options.pedantic && (e = e.replace(X.tabCharGlobal, "    ").replace(X.spaceLine, ""));
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
}, da = class {
	options;
	parser;
	constructor(e) {
		this.options = e || Ir;
	}
	space(e) {
		return "";
	}
	code({ text: e, lang: t, escaped: n }) {
		let r = (t || "").match(X.notSpaceStart)?.[0], i = e.replace(X.endingNewline, "") + "\n";
		return r ? "<pre><code class=\"language-" + ea(r) + "\">" + (n ? i : ea(i, !0)) + "</code></pre>\n" : "<pre><code>" + (n ? i : ea(i, !0)) + "</code></pre>\n";
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
		return `<code>${ea(e, !0)}</code>`;
	}
	br(e) {
		return "<br>";
	}
	del({ tokens: e }) {
		return `<del>${this.parser.parseInline(e)}</del>`;
	}
	link({ href: e, title: t, tokens: n }) {
		let r = this.parser.parseInline(n), i = ta(e);
		if (i === null) return r;
		e = i;
		let a = "<a href=\"" + e + "\"";
		return t && (a += " title=\"" + ea(t) + "\""), a += ">" + r + "</a>", a;
	}
	image({ href: e, title: t, text: n, tokens: r }) {
		r && (n = this.parser.parseInline(r, this.parser.textRenderer));
		let i = ta(e);
		if (i === null) return ea(n);
		e = i;
		let a = `<img src="${e}" alt="${ea(n)}"`;
		return t && (a += ` title="${ea(t)}"`), a += ">", a;
	}
	text(e) {
		return "tokens" in e && e.tokens ? this.parser.parseInline(e.tokens) : "escaped" in e && e.escaped ? e.text : ea(e.text);
	}
}, fa = class {
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
}, pa = class e {
	options;
	renderer;
	textRenderer;
	constructor(e) {
		this.options = e || Ir, this.options.renderer = this.options.renderer || new da(), this.renderer = this.options.renderer, this.renderer.options = this.options, this.renderer.parser = this, this.textRenderer = new fa();
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
}, ma = class {
	options;
	block;
	constructor(e) {
		this.options = e || Ir;
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
		return e ? ua.lex : ua.lexInline;
	}
	provideParser(e = this.block) {
		return e ? pa.parse : pa.parseInline;
	}
}, ha = class {
	defaults = Fr();
	options = this.setOptions;
	parse = this.parseMarkdown(!0);
	parseInline = this.parseMarkdown(!1);
	Parser = pa;
	Renderer = da;
	TextRenderer = fa;
	Lexer = ua;
	Tokenizer = la;
	Hooks = ma;
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
				let t = this.defaults.renderer || new da(this.defaults);
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
				let t = this.defaults.tokenizer || new la(this.defaults);
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
				let t = this.defaults.hooks || new ma();
				for (let n in e.hooks) {
					if (!(n in t)) throw Error(`hook '${n}' does not exist`);
					if (["options", "block"].includes(n)) continue;
					let r = n, i = e.hooks[r], a = t[r];
					t[r] = ma.passThroughHooks.has(n) ? (e) => {
						if (this.defaults.async && ma.passThroughHooksRespectAsync.has(n)) return (async () => {
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
		return ua.lex(e, t ?? this.defaults);
	}
	parser(e, t) {
		return pa.parse(e, t ?? this.defaults);
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
				let n = i.hooks ? await i.hooks.preprocess(t) : t, r = await (i.hooks ? await i.hooks.provideLexer(e) : e ? ua.lex : ua.lexInline)(n, i), a = i.hooks ? await i.hooks.processAllTokens(r) : r;
				i.walkTokens && await Promise.all(this.walkTokens(a, i.walkTokens));
				let o = await (i.hooks ? await i.hooks.provideParser(e) : e ? pa.parse : pa.parseInline)(a, i);
				return i.hooks ? await i.hooks.postprocess(o) : o;
			})().catch(a);
			try {
				i.hooks && (t = i.hooks.preprocess(t));
				let n = (i.hooks ? i.hooks.provideLexer(e) : e ? ua.lex : ua.lexInline)(t, i);
				i.hooks && (n = i.hooks.processAllTokens(n)), i.walkTokens && this.walkTokens(n, i.walkTokens);
				let r = (i.hooks ? i.hooks.provideParser(e) : e ? pa.parse : pa.parseInline)(n, i);
				return i.hooks && (r = i.hooks.postprocess(r)), r;
			} catch (e) {
				return a(e);
			}
		};
	}
	onError(e, t) {
		return (n) => {
			if (n.message += "\nPlease report this to https://github.com/markedjs/marked.", e) {
				let e = "<p>An error occurred:</p><pre>" + ea(n.message + "", !0) + "</pre>";
				return t ? Promise.resolve(e) : e;
			}
			if (t) return Promise.reject(n);
			throw n;
		};
	}
}, ga = new ha();
function Z(e, t) {
	return ga.parse(e, t);
}
Z.options = Z.setOptions = function(e) {
	return ga.setOptions(e), Z.defaults = ga.defaults, Lr(Z.defaults), Z;
}, Z.getDefaults = Fr, Z.defaults = Ir;
function _a(...e) {
	return ga.use(...e), Z.defaults = ga.defaults, Lr(Z.defaults), Z;
}
Z.use = _a, Z.walkTokens = function(e, t) {
	return ga.walkTokens(e, t);
}, Z.parseInline = ga.parseInline, Z.Parser = pa, Z.parser = pa.parse, Z.Renderer = da, Z.TextRenderer = fa, Z.Lexer = ua, Z.lexer = ua.lex, Z.Tokenizer = la, Z.Hooks = ma, Z.parse = Z, Z.options, Z.setOptions, Z.walkTokens, Z.parseInline, pa.parse, ua.lex;
//#endregion
//#region src/presentation.ts
var va = {
	accept: "Continue",
	addContext: "Add context",
	agentName: (e) => e ? `${ya(e)} Agent` : "Agent",
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
	closeSession: "Close session",
	commands: "Commands",
	composerPlaceholder: "Ask anything…",
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
	sessionPhase: (e) => ya(e),
	sessionUntitled: "Untitled session",
	sessions: "Sessions",
	stop: "Stop",
	thinking: "Thinking",
	terminalOutputInActivity: "Terminal output is shown in the activity stream.",
	tool: "Tool",
	toolInput: "Input",
	toolOutput: "Output",
	toolResult: "tool result",
	unsupportedContent: (e) => `Unsupported agent content: ${e}`,
	unsafeResourceLink: "unsafe resource link",
	usage: (e, t) => `${ba(e)} / ${ba(t)}`,
	you: "You",
	confirmDeleteSession: (e) => `Delete “${e}”?`,
	backToSession: (e) => `Back to ${e}`
};
function ya(e) {
	return e.replaceAll(/[_-]+/g, " ").trim().replaceAll(/(^|\s)\S/g, (e) => e.toUpperCase());
}
function ba(e) {
	return e < 0xe8d4a51000 ? e.toLocaleString() : e.toExponential(2);
}
//#endregion
//#region node_modules/.pnpm/preact@10.29.8/node_modules/preact/jsx-runtime/dist/jsxRuntime.module.js
var xa = 0;
Array.isArray;
function Q(e, t, n, r, i, a) {
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
		__v: --xa,
		__i: -1,
		__u: 0,
		__source: i,
		__self: a
	};
	if (typeof e == "function" && (o = e.defaultProps)) for (s in o) c[s] === void 0 && (c[s] = o[s]);
	return w.vnode && w.vnode(l), l;
}
//#endregion
//#region src/react/Chat.tsx
var Sa = ze(void 0), Ca = /* @__PURE__ */ new WeakMap(), wa = 0, Ta = {
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
}, Ea = {
	ready: new Promise(() => void 0),
	getSnapshot: () => Ta,
	subscribe: () => () => void 0,
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
function Da(e) {
	let t = tt(Sa);
	if (!t) throw Error(`pretty-aui: ${e} must be rendered inside a ChatRoot.`);
	return t;
}
function Oa(e) {
	return /* @__PURE__ */ Q(ka, {
		...e,
		children: [
			/* @__PURE__ */ Q(Ma, {}),
			/* @__PURE__ */ Q(Na, {}),
			/* @__PURE__ */ Q(Pa, {}),
			/* @__PURE__ */ Q(oo, {})
		]
	});
}
function ka(e) {
	if ("controller" in e) {
		let { controller: t, ...n } = e;
		return /* @__PURE__ */ Q(ja, {
			...n,
			controller: t
		}, To(t));
	}
	let { options: t, ...n } = e;
	return /* @__PURE__ */ Q(Aa, {
		...n,
		options: t
	});
}
function Aa(e) {
	let { options: t, ...n } = e, r = L(t), [i, a] = F();
	return I(() => {
		let e = rn(r.current);
		return a(e), () => {
			e.destroy();
		};
	}, []), i ? /* @__PURE__ */ Q(ja, {
		...n,
		controller: i
	}, To(i)) : /* @__PURE__ */ Q(ja, {
		...n,
		controller: Ea
	}, "connecting");
}
function ja(e) {
	let { controller: t } = e, n = dt(et((e) => Do(t, e), [t]), et(() => t.getSnapshot(), [t]), et(() => t.getSnapshot(), [t])), r = $e(() => ({
		...va,
		...e.labels
	}), [e.labels]), i = nt().replaceAll(":", ""), [a, o] = F(), s = et((e) => {
		o(void 0), e().catch((e) => {
			o(e instanceof Error ? e.message : String(e));
		});
	}, []), c = e.colorScheme ?? "system", l = e.surface ?? "inline", u = $e(() => ({
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
	return /* @__PURE__ */ Q("section", {
		className: ["pretty-aui", e.className].filter(Boolean).join(" "),
		"data-pretty-aui-slot": "root",
		"data-surface": l,
		"data-scheme": c,
		"data-phase": n.phase,
		style: e.style,
		"aria-label": n.agentName ?? r.assistantName,
		children: /* @__PURE__ */ Q(Sa.Provider, {
			value: u,
			children: e.children
		})
	});
}
function Ma() {
	let { controller: e, snapshot: t, labels: n, runAction: r } = Da("ChatHeader"), [i, a] = F(!1), o = t.sessionTitle ?? n.sessionUntitled, s = t.sessionTrail.at(-1), c = t.protocolVersion !== void 0 && t.phase !== "connecting" && t.phase !== "auth_required" && t.phase !== "closed" && t.loadedSessions.length < 16;
	return /* @__PURE__ */ Q(D, { children: [/* @__PURE__ */ Q("header", {
		className: "paui-header",
		"data-pretty-aui-slot": "header",
		children: [/* @__PURE__ */ Q("div", {
			className: `paui-identity${s ? " paui-identity--child" : ""}`,
			children: [/* @__PURE__ */ Q("span", {
				className: "paui-presence",
				"data-phase": t.phase,
				"aria-hidden": "true"
			}), s ? /* @__PURE__ */ Q("div", {
				className: "paui-lineage",
				"data-depth": t.sessionTrail.length,
				children: [
					/* @__PURE__ */ Q("button", {
						className: "paui-lineage__back",
						type: "button",
						disabled: t.phase !== "idle",
						"aria-label": n.backToSession(s.title ?? s.sessionId),
						onClick: () => r(() => e.openAncestorSession(s.sessionId)),
						children: /* @__PURE__ */ Q(Vo, {})
					}),
					/* @__PURE__ */ Q("div", {
						className: "paui-lineage__titles",
						children: [t.sessionTrail.map((n) => {
							let i = n.title ?? n.sessionId;
							return /* @__PURE__ */ Q("span", {
								className: "paui-lineage__ancestor",
								children: [/* @__PURE__ */ Q("button", {
									type: "button",
									disabled: t.phase !== "idle",
									onClick: () => r(() => e.openAncestorSession(n.sessionId)),
									children: i
								}), /* @__PURE__ */ Q("span", {
									"aria-hidden": "true",
									children: "/"
								})]
							}, n.sessionId);
						}), /* @__PURE__ */ Q("strong", { children: o })]
					}),
					/* @__PURE__ */ Q("span", {
						className: "paui-protocol",
						children: t.protocolVersion ? `ACP v${t.protocolVersion}` : t.phase
					})
				]
			}) : /* @__PURE__ */ Q("div", { children: [/* @__PURE__ */ Q("strong", { children: o }), /* @__PURE__ */ Q("span", {
				className: "paui-protocol",
				children: t.protocolVersion ? `ACP v${t.protocolVersion}` : t.phase
			})] })]
		}), /* @__PURE__ */ Q("div", {
			className: "paui-header__actions",
			children: [
				t.usage ? /* @__PURE__ */ Q("span", {
					className: "paui-usage",
					children: n.usage(t.usage.used, t.usage.size)
				}) : null,
				t.capabilities.listSessions || t.loadedSessions.length > 1 ? /* @__PURE__ */ Q("button", {
					className: "paui-icon-button",
					type: "button",
					onClick: () => a(!0),
					children: [/* @__PURE__ */ Q(Po, {}), /* @__PURE__ */ Q("span", {
						className: "paui-sr-only",
						children: n.sessions
					})]
				}) : null,
				/* @__PURE__ */ Q("button", {
					className: "paui-icon-button",
					type: "button",
					disabled: !c,
					onClick: () => r(() => e.newSession()),
					children: [/* @__PURE__ */ Q(Fo, {}), /* @__PURE__ */ Q("span", {
						className: "paui-sr-only",
						children: n.newChat
					})]
				})
			]
		})]
	}), i ? /* @__PURE__ */ Q(mo, {
		controller: e,
		snapshot: t,
		labels: n,
		onClose: () => a(!1)
	}) : null] });
}
function Na() {
	let { snapshot: e, labels: t, toolActivityRenderer: n } = Da("ChatTranscript"), r = L(null), i = L(null), a = L(!0), o = L(0), s = Eo(e), c = L(s), l = L(/* @__PURE__ */ new Map()), [u, d] = F(!0), f = et((e = "auto") => {
		let t = r.current;
		t && (typeof t.scrollTo == "function" ? t.scrollTo({
			top: t.scrollHeight,
			behavior: e
		}) : t.scrollTop = t.scrollHeight, o.current = t.scrollTop, a.current = !0, d(!0));
	}, []), p = et(() => {
		let e = r.current;
		if (!e) return;
		let t = e.scrollHeight - e.scrollTop - e.clientHeight, n = e.scrollTop < o.current - 1, i = t <= 24 || !n && a.current;
		o.current = e.scrollTop, a.current = i, l.current.set(s, {
			top: e.scrollTop,
			pinned: i
		}), d(i);
	}, [s]);
	Qe(() => {
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
	}, [f, s]), Qe(() => {
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
	let m = $e(() => Fa(e.activities), [e.activities]);
	return /* @__PURE__ */ Q(D, { children: [/* @__PURE__ */ Q("main", {
		ref: r,
		className: "paui-body",
		"data-pretty-aui-slot": "transcript",
		tabIndex: 0,
		onScroll: p,
		children: /* @__PURE__ */ Q("div", {
			className: "paui-transcript",
			ref: i,
			children: [
				e.historyGap ? /* @__PURE__ */ Q("aside", {
					className: "paui-notice",
					role: "status",
					children: [/* @__PURE__ */ Q(ns, {}), /* @__PURE__ */ Q("div", { children: [/* @__PURE__ */ Q("strong", { children: t.historyGapTitle }), /* @__PURE__ */ Q("span", { children: t.historyGap })] })]
				}) : null,
				e.activities.length ? null : /* @__PURE__ */ Q("div", {
					className: "paui-empty",
					children: [
						/* @__PURE__ */ Q(rs, {}),
						/* @__PURE__ */ Q("strong", { children: t.emptyTitle }),
						/* @__PURE__ */ Q("p", { children: t.emptyDescription })
					]
				}),
				m.map((r, i) => /* @__PURE__ */ Q(Ia, {
					group: r,
					labels: t,
					toolActivityRenderer: n,
					active: i === m.length - 1 && (e.phase === "running" || e.phase === "awaiting_user" || e.phase === "cancelling")
				}, r.id))
			]
		})
	}), u ? null : /* @__PURE__ */ Q("div", {
		className: "paui-to-bottom-row",
		children: /* @__PURE__ */ Q("button", {
			className: "paui-to-bottom",
			type: "button",
			onClick: () => f("smooth"),
			"aria-label": t.scrollToLatest,
			children: /* @__PURE__ */ Q(Bo, {})
		})
	})] });
}
function Pa() {
	let { controller: e, snapshot: t, labels: n, actionError: r, runAction: i } = Da("ChatInteractions"), a = L(null);
	return I(() => {
		if (!t.interactions.length) return;
		let e = a.current;
		if (!e) return;
		let n = go(e);
		n && e.contains(n) || e.querySelector(yo)?.focus();
	}, [t.interactions.map((e) => e.id).join("\0"), t.interactions.length]), /* @__PURE__ */ Q("div", {
		ref: a,
		className: "paui-interactions",
		"data-pretty-aui-slot": "interactions",
		children: [
			t.phase === "auth_required" ? /* @__PURE__ */ Q(po, {}) : null,
			t.interactions.map((t) => t.type === "permission" ? /* @__PURE__ */ Q(co, {
				interaction: t,
				controller: e,
				labels: n
			}, t.id) : /* @__PURE__ */ Q(lo, {
				interaction: t,
				controller: e,
				labels: n
			}, t.id)),
			t.error ? /* @__PURE__ */ Q("aside", {
				className: "paui-error",
				role: "alert",
				children: [/* @__PURE__ */ Q("div", { children: [/* @__PURE__ */ Q("strong", { children: n.error }), /* @__PURE__ */ Q("span", { children: t.error.message })] }), t.error.retryable ? /* @__PURE__ */ Q("button", {
					type: "button",
					onClick: () => i(() => e.reconnect()),
					children: n.retry
				}) : null]
			}) : null,
			r && !t.error ? /* @__PURE__ */ Q("aside", {
				className: "paui-error",
				role: "alert",
				children: /* @__PURE__ */ Q("div", { children: [/* @__PURE__ */ Q("strong", { children: n.error }), /* @__PURE__ */ Q("span", { children: r })] })
			}) : null
		]
	});
}
function Fa(e) {
	let t = [], n = "opening", r, i = [], a = () => {
		(r || i.length) && t.push({
			id: n,
			...r ? { user: r } : {},
			activities: i
		});
	};
	for (let t of e) t.type === "message" && t.role === "user" ? (a(), n = t.id, r = t, i = []) : i.push(t);
	return a(), t;
}
function Ia({ group: e, labels: t, toolActivityRenderer: n, active: r }) {
	return /* @__PURE__ */ Q("article", {
		className: "paui-turn",
		children: [e.user ? /* @__PURE__ */ Q(qa, {
			message: e.user,
			labels: t
		}) : null, e.activities.length ? /* @__PURE__ */ Q("div", {
			className: "paui-activities",
			children: e.activities.map((i, a) => /* @__PURE__ */ Q(La, {
				activity: i,
				labels: t,
				toolActivityRenderer: n,
				running: r && a === e.activities.length - 1
			}, i.id))
		}) : null]
	});
}
var La = mt(function({ activity: e, labels: t, toolActivityRenderer: n, running: r }) {
	return /* @__PURE__ */ Q("div", {
		className: "paui-activity",
		"data-pretty-aui-slot": "activity",
		"data-kind": e.type === "message" ? e.role : e.type === "tool" && e.subagent ? "subagent" : e.type,
		"data-status": ko(e),
		children: /* @__PURE__ */ Q(Ra, {
			activity: e,
			labels: t,
			toolActivityRenderer: n,
			running: r
		})
	});
});
function Ra({ activity: e, labels: t, toolActivityRenderer: n, running: r }) {
	switch (e.type) {
		case "message": return /* @__PURE__ */ Q(qa, {
			message: e,
			labels: t,
			running: r
		});
		case "context": return /* @__PURE__ */ Q(za, {
			activity: e,
			labels: t
		});
		case "tool": return e.subagent ? /* @__PURE__ */ Q(Ua, {
			tool: e,
			labels: t,
			renderer: n
		}) : /* @__PURE__ */ Q("details", {
			className: "paui-disclosure paui-tool",
			"data-state": e.status,
			children: [/* @__PURE__ */ Q("summary", {
				className: "paui-flow-summary",
				children: [
					/* @__PURE__ */ Q(Ya, { icon: /* @__PURE__ */ Q($a, { kind: e.kind }) }),
					/* @__PURE__ */ Q("span", {
						className: "paui-flow-title",
						children: Qa(e.kind, t.tool)
					}),
					/* @__PURE__ */ Q("span", {
						className: "paui-flow-separator",
						"aria-hidden": "true"
					}),
					/* @__PURE__ */ Q("span", {
						className: "paui-flow-preview",
						children: e.title
					}),
					/* @__PURE__ */ Q("span", {
						className: "paui-sr-only",
						children: e.status
					})
				]
			}), /* @__PURE__ */ Q("div", {
				className: "paui-disclosure__body",
				children: /* @__PURE__ */ Q(eo, {
					tool: e,
					labels: t,
					renderer: n
				})
			})]
		});
		case "plan": return /* @__PURE__ */ Q("details", {
			className: "paui-disclosure paui-plan",
			open: !0,
			children: [/* @__PURE__ */ Q("summary", { children: [
				/* @__PURE__ */ Q(Ko, {}),
				/* @__PURE__ */ Q("span", { children: t.plan }),
				/* @__PURE__ */ Q(No, { status: Oo(e.entries) })
			] }), /* @__PURE__ */ Q("ol", {
				className: "paui-plan__list",
				children: e.entries.map((e, t) => /* @__PURE__ */ Q("li", {
					"data-status": e.status,
					children: [/* @__PURE__ */ Q("span", {
						className: "paui-plan__mark",
						"aria-hidden": "true"
					}), /* @__PURE__ */ Q("span", { children: e.content })]
				}, `${e.content}-${t}`))
			})]
		});
		case "terminal": return /* @__PURE__ */ Q("details", {
			className: "paui-disclosure paui-terminal",
			children: [/* @__PURE__ */ Q("summary", { children: [
				/* @__PURE__ */ Q(Xo, {}),
				/* @__PURE__ */ Q("span", { children: e.title }),
				/* @__PURE__ */ Q(No, { status: e.exited ? "completed" : "in_progress" })
			] }), /* @__PURE__ */ Q("pre", { children: e.output })]
		});
		case "unsupported": return /* @__PURE__ */ Q("div", {
			className: "paui-unsupported",
			children: t.unsupportedContent(e.kind)
		});
	}
}
function za({ activity: e, labels: t }) {
	return /* @__PURE__ */ Q("details", {
		className: "paui-disclosure paui-context-injection",
		children: [/* @__PURE__ */ Q("summary", {
			className: "paui-flow-summary",
			children: [
				/* @__PURE__ */ Q(Ya, { icon: /* @__PURE__ */ Q(ts, {}) }),
				/* @__PURE__ */ Q("span", {
					className: "paui-flow-title",
					children: t.contextInjection
				}),
				/* @__PURE__ */ Q("span", {
					className: "paui-flow-separator",
					"aria-hidden": "true"
				}),
				/* @__PURE__ */ Q("span", {
					className: "paui-flow-preview",
					children: e.label
				})
			]
		}), /* @__PURE__ */ Q("div", {
			className: "paui-context-injection__body",
			tabIndex: 0,
			children: e.content.map((n, r) => /* @__PURE__ */ Q(Ba, {
				block: n,
				labels: t
			}, `${e.id}:${r}`))
		})]
	});
}
function Ba({ block: e, labels: t }) {
	if (e.type === "text" && typeof e.text == "string") return /* @__PURE__ */ Q(Va, {
		text: e.text,
		labels: t
	});
	if (e.type === "resource" && Mo(e.resource)) {
		let n = e.resource;
		return /* @__PURE__ */ Q("section", {
			className: "paui-context-block",
			children: [/* @__PURE__ */ Q("div", {
				className: "paui-context-meta",
				children: [/* @__PURE__ */ Q("span", { children: String(n.uri ?? t.resource) }), typeof n.mimeType == "string" ? /* @__PURE__ */ Q("span", { children: n.mimeType }) : null]
			}), typeof n.text == "string" ? /* @__PURE__ */ Q(Va, {
				text: n.text,
				labels: t
			}) : typeof n.blob == "string" ? /* @__PURE__ */ Q("span", {
				className: "paui-muted",
				children: `Binary resource · ${n.blob.length.toLocaleString()} base64 characters`
			}) : null]
		});
	}
	if (e.type === "resource_link" && typeof e.uri == "string") {
		let n = typeof e.title == "string" ? e.title : typeof e.name == "string" ? e.name : t.resource, r = typeof e.mimeType == "string" ? e.mimeType : void 0, i = typeof e.description == "string" ? e.description : void 0;
		return /* @__PURE__ */ Q("section", {
			className: "paui-context-block",
			children: [
				/* @__PURE__ */ Q("div", {
					className: "paui-context-meta",
					children: [/* @__PURE__ */ Q("span", { children: n }), r ? /* @__PURE__ */ Q("span", { children: r }) : null]
				}),
				/* @__PURE__ */ Q("span", {
					className: "paui-context-identifier",
					children: e.uri
				}),
				i ? /* @__PURE__ */ Q("span", { children: i }) : null
			]
		});
	}
	return (e.type === "image" || e.type === "audio") && typeof e.mimeType == "string" && typeof e.data == "string" ? /* @__PURE__ */ Q("span", {
		className: "paui-context-meta",
		children: `${Qa(e.type, e.type)} · ${e.mimeType} · ${e.data.length.toLocaleString()} base64 characters`
	}) : /* @__PURE__ */ Q(Va, {
		text: _o(e),
		labels: t
	});
}
function Va({ text: e, labels: t }) {
	let n = Ha(e);
	return /* @__PURE__ */ Q(D, { children: [/* @__PURE__ */ Q("pre", {
		className: "paui-context-text",
		children: n.text
	}), n.truncated ? /* @__PURE__ */ Q("span", {
		className: "paui-context-truncated",
		children: t.contextTruncated(e.length)
	}) : null] });
}
function Ha(e) {
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
function Ua({ tool: e, labels: t, renderer: n }) {
	let { controller: r, snapshot: i, runAction: a } = Da("ChatTranscript"), o = e.subagent, s = e.status === "pending" || e.status === "in_progress", c = Wa(e.id, s), l = Ka(e, t), u = i.capabilities.loadSession || i.capabilities.resumeSession;
	return /* @__PURE__ */ Q("div", {
		className: "paui-subagent-row",
		children: [/* @__PURE__ */ Q("details", {
			className: "paui-disclosure paui-subagent",
			"data-state": e.status,
			"data-running": s || void 0,
			children: [/* @__PURE__ */ Q("summary", {
				className: "paui-flow-summary",
				children: [
					/* @__PURE__ */ Q(Ya, { icon: /* @__PURE__ */ Q(Wo, {}) }),
					/* @__PURE__ */ Q("span", {
						className: "paui-flow-title",
						children: t.agentName(o.agent)
					}),
					o.description ? /* @__PURE__ */ Q(D, { children: [/* @__PURE__ */ Q("span", {
						className: "paui-flow-separator",
						"aria-hidden": "true"
					}), /* @__PURE__ */ Q("span", {
						className: "paui-flow-preview",
						children: o.description
					})] }) : null,
					/* @__PURE__ */ Q("span", {
						className: "paui-subagent-status",
						"data-status": e.status,
						children: [s ? /* @__PURE__ */ Q("span", {
							className: "paui-subagent-status__ongoing",
							children: [/* @__PURE__ */ Q("span", {
								className: "paui-subagent-status__spinner",
								"aria-hidden": "true"
							}), /* @__PURE__ */ Q("span", { children: t.agentOngoing })]
						}) : /* @__PURE__ */ Q("span", { children: l }), c ? /* @__PURE__ */ Q("span", { children: t.agentObserved(c) }) : null]
					})
				]
			}), /* @__PURE__ */ Q("div", {
				className: "paui-disclosure__body",
				children: /* @__PURE__ */ Q(eo, {
					tool: e,
					labels: t,
					renderer: n
				})
			})]
		}), o.sessionId ? /* @__PURE__ */ Q("button", {
			className: "paui-subagent-open",
			type: "button",
			disabled: !u || i.phase !== "idle",
			"aria-label": t.openChildSession,
			onClick: () => a(() => r.openChildSession(o.sessionId)),
			children: /* @__PURE__ */ Q(Go, {})
		}) : null]
	});
}
function Wa(e, t) {
	let n = L(Date.now()), [r, i] = F(n.current);
	return I(() => {
		n.current = Date.now(), i(n.current);
	}, [e]), I(() => {
		if (!t) return;
		let e = window.setInterval(() => i(Date.now()), 1e3);
		return () => window.clearInterval(e);
	}, [t]), t ? Ga(r - n.current) : void 0;
}
function Ga(e) {
	let t = Math.max(0, Math.floor(e / 1e3));
	if (t < 60) return `${t}s`;
	let n = Math.floor(t / 60), r = t % 60;
	return n < 60 ? `${n}m ${String(r).padStart(2, "0")}s` : `${Math.floor(n / 60)}h ${String(n % 60).padStart(2, "0")}m`;
}
function Ka(e, t) {
	return e.subagent?.background && e.status === "completed" ? t.agentBackground : e.status === "completed" ? t.agentCompleted : e.status === "failed" ? t.agentFailed : e.status === "cancelled" ? t.agentCancelled : Qa(e.status, t.agentCompleted);
}
function qa({ message: e, labels: t, running: n = !1 }) {
	return e.role === "thought" ? /* @__PURE__ */ Q(Ja, {
		message: e,
		labels: t,
		running: n
	}) : /* @__PURE__ */ Q("div", {
		className: "paui-message",
		"data-pretty-aui-slot": "message",
		"data-role": e.role,
		"data-pending": e.pending || void 0,
		"aria-live": e.role === "assistant" && n ? "polite" : void 0,
		"aria-atomic": e.role === "assistant" && n ? "false" : void 0,
		children: [/* @__PURE__ */ Q("span", {
			className: "paui-message__label",
			children: e.role === "user" ? t.you : t.assistantName
		}), /* @__PURE__ */ Q("div", {
			className: "paui-message__content",
			children: e.content.map((e, n) => /* @__PURE__ */ Q(io, {
				block: e,
				labels: t
			}, n))
		})]
	});
}
function Ja({ message: e, labels: t, running: n }) {
	let r = L(null), i = Xa(e.content, n);
	return Qe(() => {
		let e = r.current;
		e && (e.scrollLeft = n ? e.scrollWidth - e.clientWidth : 0);
	}, [i, n]), /* @__PURE__ */ Q("details", {
		className: "paui-thought",
		"data-running": n || void 0,
		children: [/* @__PURE__ */ Q("summary", {
			className: "paui-flow-summary",
			children: [
				/* @__PURE__ */ Q(Ya, { icon: /* @__PURE__ */ Q(qo, {}) }),
				/* @__PURE__ */ Q("span", {
					className: "paui-flow-title",
					children: t.thinking
				}),
				i ? /* @__PURE__ */ Q(D, { children: [/* @__PURE__ */ Q("span", {
					className: "paui-flow-separator",
					"aria-hidden": "true"
				}), /* @__PURE__ */ Q("span", {
					ref: r,
					className: "paui-flow-preview",
					"data-follow-end": n || void 0,
					children: i
				})] }) : null
			]
		}), /* @__PURE__ */ Q("div", {
			className: "paui-thought__body",
			children: e.content.map((e, n) => /* @__PURE__ */ Q(io, {
				block: e,
				labels: t
			}, n))
		})]
	});
}
function Ya({ icon: e }) {
	return /* @__PURE__ */ Q("span", {
		className: "paui-flow-leading",
		"aria-hidden": "true",
		children: [/* @__PURE__ */ Q("span", {
			className: "paui-flow-icon",
			children: e
		}), /* @__PURE__ */ Q("span", {
			className: "paui-flow-chevron",
			children: /* @__PURE__ */ Q(Ho, {})
		})]
	});
}
function Xa(e, t) {
	if (t) {
		for (let t = e.length - 1; t >= 0; --t) {
			let n = Za(e[t]).trimEnd();
			if (n) return n.slice(n.lastIndexOf("\n") + 1).replace(/\r$/, "").trim();
		}
		return "";
	}
	let n = e.map(Za).filter(Boolean).join("\n").trimEnd();
	return n ? n.split(/\r?\n/)[0]?.trim() ?? "" : "";
}
function Za(e) {
	return e.type === "text" && typeof e.text == "string" ? e.text : e.type === "resource" && Mo(e.resource) && typeof e.resource.text == "string" ? e.resource.text : "";
}
function Qa(e, t) {
	if (!e) return t;
	let n = e.replaceAll(/[_-]+/g, " ").trim();
	return n ? `${n[0].toUpperCase()}${n.slice(1)}` : t;
}
function $a({ kind: e }) {
	let t = e?.toLowerCase() ?? "";
	return t.includes("read") || t.includes("browse") || t.includes("context") ? /* @__PURE__ */ Q(Jo, {}) : t.includes("search") || t.includes("find") ? /* @__PURE__ */ Q(Yo, {}) : t.includes("bash") || t.includes("shell") || t.includes("terminal") || t.includes("execute") ? /* @__PURE__ */ Q(Xo, {}) : /* @__PURE__ */ Q(Uo, {});
}
function eo({ tool: e, labels: t, renderer: n }) {
	let r = /* @__PURE__ */ Q(to, {
		tool: e,
		labels: t
	});
	return n ? /* @__PURE__ */ Q(ro, {
		fallback: r,
		resetKey: e.id,
		children: /* @__PURE__ */ Q(no, {
			tool: e,
			renderer: n,
			fallback: r
		})
	}, e.id) : r;
}
function to({ tool: e, labels: t }) {
	return e.content.length ? e.content.map((e, n) => /* @__PURE__ */ Q(ao, {
		value: e,
		labels: t
	}, n)) : e.rawInput === void 0 && e.rawOutput === void 0 ? /* @__PURE__ */ Q("span", {
		className: "paui-muted",
		children: t.tool
	}) : /* @__PURE__ */ Q("div", {
		className: "paui-tool-raw",
		children: [e.rawInput === void 0 ? null : /* @__PURE__ */ Q("section", { children: [/* @__PURE__ */ Q("strong", { children: t.toolInput }), /* @__PURE__ */ Q("pre", { children: _o(e.rawInput) })] }), e.rawOutput === void 0 ? null : /* @__PURE__ */ Q("section", { children: [/* @__PURE__ */ Q("strong", { children: t.toolOutput }), /* @__PURE__ */ Q("pre", { children: _o(e.rawOutput) })] })]
	});
}
function no({ tool: e, renderer: t, fallback: n }) {
	let r = t(e);
	return r === void 0 ? n : r;
}
var ro = class extends O {
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
function io({ block: e, labels: t }) {
	let n = $e(() => e.type === "text" && typeof e.text == "string" ? xo(e.text) : void 0, [e]);
	if (n !== void 0) return /* @__PURE__ */ Q("div", {
		className: "paui-markdown",
		dangerouslySetInnerHTML: { __html: n }
	});
	if (e.type === "image" && typeof e.data == "string" && typeof e.mimeType == "string" && e.mimeType.startsWith("image/")) return /* @__PURE__ */ Q("img", {
		className: "paui-media",
		src: `data:${e.mimeType};base64,${e.data}`,
		alt: ""
	});
	if (e.type === "audio" && typeof e.data == "string" && typeof e.mimeType == "string" && e.mimeType.startsWith("audio/")) return /* @__PURE__ */ Q("audio", {
		className: "paui-media",
		controls: !0,
		src: `data:${e.mimeType};base64,${e.data}`
	});
	if (e.type === "resource_link" && typeof e.uri == "string") {
		let n = typeof e.title == "string" ? e.title : typeof e.name == "string" ? e.name : e.uri;
		return wo(e.uri) ? /* @__PURE__ */ Q("a", {
			className: "paui-resource",
			href: e.uri,
			target: "_blank",
			rel: "noreferrer",
			children: [/* @__PURE__ */ Q(Qo, {}), /* @__PURE__ */ Q("span", { children: n })]
		}) : /* @__PURE__ */ Q("span", {
			className: "paui-unsupported",
			children: t.unsupportedContent(t.unsafeResourceLink)
		});
	}
	if (e.type === "resource" && Mo(e.resource)) {
		let n = e.resource, r = typeof n.uri == "string" ? n.uri : t.resource;
		return typeof n.text == "string" ? /* @__PURE__ */ Q("details", {
			className: "paui-resource",
			children: [/* @__PURE__ */ Q("summary", { children: [/* @__PURE__ */ Q($o, {}), r] }), /* @__PURE__ */ Q("pre", { children: n.text })]
		}) : /* @__PURE__ */ Q("span", {
			className: "paui-resource",
			children: [/* @__PURE__ */ Q($o, {}), r]
		});
	}
	return /* @__PURE__ */ Q("span", {
		className: "paui-unsupported",
		children: t.unsupportedContent(e.type)
	});
}
function ao({ value: e, labels: t }) {
	if (!Mo(e)) return null;
	if (e.type === "content" && Mo(e.content) && typeof e.content.type == "string") return /* @__PURE__ */ Q(io, {
		block: e.content,
		labels: t
	});
	if (e.type === "diff") {
		let n = typeof e.path == "string" ? e.path : t.changedFiles, r = typeof e.patch == "string" ? e.patch : typeof e.newText == "string" ? e.newText : void 0;
		return /* @__PURE__ */ Q("details", {
			className: "paui-diff",
			children: [/* @__PURE__ */ Q("summary", { children: [/* @__PURE__ */ Q(es, {}), n] }), r ? /* @__PURE__ */ Q("pre", { children: r }) : /* @__PURE__ */ Q("span", {
				className: "paui-muted",
				children: t.binaryChange
			})]
		});
	}
	return e.type === "terminal" ? /* @__PURE__ */ Q("span", {
		className: "paui-muted",
		children: [
			/* @__PURE__ */ Q(Xo, {}),
			" ",
			t.terminalOutputInActivity
		]
	}) : /* @__PURE__ */ Q("span", {
		className: "paui-unsupported",
		children: t.unsupportedContent(typeof e.type == "string" ? e.type : t.toolResult)
	});
}
function oo() {
	let { controller: e, snapshot: t, labels: n, runAction: r, ids: i } = Da("ChatComposer"), [a, o] = F(""), [s, c] = F(0), [l, u] = F(!1), d = L(!1), f = L(null), p = Eo(t), m = L(p), h = L(/* @__PURE__ */ new Map()), g = t.activities.length || t.interactions.length || t.phase === "auth_required" || t.error ? "docked" : "hero";
	I(() => {
		if (m.current !== p) {
			let e = m.current;
			h.current.set(e, a), m.current = p;
			let t = h.current.get(p);
			e === void 0 && t === void 0 && (t = a, h.current.set(p, a)), o(t ?? "");
		}
	}, [p, a]), Qe(() => {
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
	return /* @__PURE__ */ Q("footer", {
		className: "paui-composer-wrap",
		"data-pretty-aui-slot": "composer",
		"data-placement": g,
		children: [b.length ? /* @__PURE__ */ Q("div", {
			className: "paui-commands",
			role: "listbox",
			id: C,
			"aria-label": n.commands,
			children: b.map((e, t) => /* @__PURE__ */ Q("button", {
				type: "button",
				id: `${C}-${t}`,
				role: "option",
				"aria-selected": t === x,
				onMouseDown: (e) => e.preventDefault(),
				onClick: () => S(e.name),
				children: [/* @__PURE__ */ Q("code", { children: ["/", e.name] }), /* @__PURE__ */ Q("span", { children: e.description })]
			}, e.name))
		}) : null, /* @__PURE__ */ Q("div", {
			className: "paui-composer",
			"data-pretty-aui-slot": "composer-input",
			children: [
				t.contextSelection.items.length || t.contextSelection.canAdd ? /* @__PURE__ */ Q("div", {
					className: "paui-composer__context",
					"data-pretty-aui-slot": "composer-context",
					role: "group",
					"aria-label": n.contextSelection,
					children: [t.contextSelection.canAdd ? /* @__PURE__ */ Q("button", {
						className: "paui-context-add",
						type: "button",
						"aria-label": n.addContext,
						title: n.addContext,
						disabled: _ || v || t.contextSelection.busy,
						onMouseDown: (e) => e.preventDefault(),
						onClick: () => r(() => e.addContext()),
						children: /* @__PURE__ */ Q("span", {
							"aria-hidden": "true",
							children: "+"
						})
					}) : null, t.contextSelection.items.map((i) => /* @__PURE__ */ Q("span", {
						className: "paui-context-chip",
						"data-pretty-aui-slot": "composer-context-item",
						title: i.label,
						children: [/* @__PURE__ */ Q("span", {
							className: "paui-context-chip__label",
							children: i.label
						}), t.contextSelection.canRemove ? /* @__PURE__ */ Q("button", {
							type: "button",
							"aria-label": n.removeContext(i.label),
							title: n.removeContext(i.label),
							disabled: _ || v || t.contextSelection.busy,
							onMouseDown: (e) => e.preventDefault(),
							onClick: () => r(() => e.removeContext(i.id)),
							children: /* @__PURE__ */ Q("span", {
								"aria-hidden": "true",
								children: "×"
							})
						}) : null]
					}, i.id))]
				}) : null,
				/* @__PURE__ */ Q("textarea", {
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
				/* @__PURE__ */ Q("div", {
					className: "paui-composer__actions",
					"data-pretty-aui-slot": "composer-actions",
					children: [t.configOptions.length ? /* @__PURE__ */ Q(so, {
						controller: e,
						options: t.configOptions
					}) : /* @__PURE__ */ Q("span", {}), v ? /* @__PURE__ */ Q("button", {
						className: "paui-send paui-stop",
						type: "button",
						onMouseDown: (e) => e.preventDefault(),
						onClick: () => r(() => e.cancel()),
						disabled: t.phase === "cancelling",
						children: [/* @__PURE__ */ Q(zo, {}), /* @__PURE__ */ Q("span", {
							className: "paui-sr-only",
							children: n.stop
						})]
					}) : /* @__PURE__ */ Q("button", {
						className: "paui-send",
						type: "button",
						onMouseDown: (e) => e.preventDefault(),
						onClick: y,
						disabled: _ || !a.trim(),
						children: [/* @__PURE__ */ Q(Ro, {}), /* @__PURE__ */ Q("span", {
							className: "paui-sr-only",
							children: n.send
						})]
					})]
				})
			]
		})]
	});
}
function so({ controller: e, options: t }) {
	let { runAction: n } = Da("ChatComposer");
	return /* @__PURE__ */ Q("div", {
		className: "paui-config",
		children: t.map((t) => t.type === "boolean" ? /* @__PURE__ */ Q("label", {
			title: t.description,
			children: [/* @__PURE__ */ Q("input", {
				type: "checkbox",
				checked: !!t.currentValue,
				onChange: (r) => n(() => e.setConfigOption(t.id, r.target.checked))
			}), /* @__PURE__ */ Q("span", { children: t.name })]
		}, t.id) : t.type === "select" ? /* @__PURE__ */ Q("label", {
			title: t.description,
			children: [/* @__PURE__ */ Q("span", {
				className: "paui-sr-only",
				children: t.name
			}), /* @__PURE__ */ Q("select", {
				value: String(t.currentValue),
				onChange: (r) => n(() => e.setConfigOption(t.id, r.target.value)),
				children: t.options?.map((e) => /* @__PURE__ */ Q("option", {
					value: e.value,
					children: e.name
				}, e.value))
			})]
		}, t.id) : null)
	});
}
function co({ interaction: e, controller: t, labels: n }) {
	let { ids: r } = Da("ChatInteractions"), i = `${r.instance}-${e.id}-title`;
	return /* @__PURE__ */ Q("section", {
		className: "paui-interaction",
		role: "alertdialog",
		"aria-labelledby": i,
		children: [/* @__PURE__ */ Q("div", {
			className: "paui-interaction__icon",
			children: /* @__PURE__ */ Q(Zo, {})
		}), /* @__PURE__ */ Q("div", {
			className: "paui-interaction__content",
			children: [
				/* @__PURE__ */ Q("strong", {
					id: i,
					children: e.title || n.permission
				}),
				e.description ? /* @__PURE__ */ Q("p", { children: e.description }) : null,
				/* @__PURE__ */ Q("div", {
					className: "paui-interaction__actions",
					children: [e.options.map((n, r) => /* @__PURE__ */ Q("button", {
						type: "button",
						className: n.kind.startsWith("reject") ? "paui-button-secondary" : r === 0 ? "paui-button-primary" : "paui-button-secondary",
						onClick: () => t.respondPermission(e.id, {
							outcome: "selected",
							optionId: n.id
						}),
						children: n.name
					}, n.id)), /* @__PURE__ */ Q("button", {
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
function lo({ interaction: e, controller: t, labels: n }) {
	let { ids: r } = Da("ChatInteractions"), i = `${r.instance}-${e.id}-title`;
	if (e.mode === "url" && e.url) {
		let r = wo(e.url);
		return /* @__PURE__ */ Q("section", {
			className: "paui-interaction",
			role: "dialog",
			"aria-labelledby": i,
			children: [/* @__PURE__ */ Q("div", {
				className: "paui-interaction__icon",
				children: /* @__PURE__ */ Q(Qo, {})
			}), /* @__PURE__ */ Q("div", {
				className: "paui-interaction__content",
				children: [
					/* @__PURE__ */ Q("strong", {
						id: i,
						children: e.message
					}),
					/* @__PURE__ */ Q("code", {
						className: "paui-url",
						children: e.url
					}),
					/* @__PURE__ */ Q("div", {
						className: "paui-interaction__actions",
						children: [
							/* @__PURE__ */ Q("button", {
								className: "paui-button-primary",
								type: "button",
								disabled: !r,
								onClick: () => r ? window.open(e.url, "_blank", "noopener,noreferrer") : void 0,
								children: n.openLink
							}),
							/* @__PURE__ */ Q("button", {
								className: "paui-button-secondary",
								type: "button",
								onClick: () => t.respondElicitation(e.id, { action: "accept" }),
								children: n.finish
							}),
							/* @__PURE__ */ Q("button", {
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
	return /* @__PURE__ */ Q(uo, {
		interaction: e,
		controller: t,
		labels: n,
		titleId: i
	});
}
function uo({ interaction: e, controller: t, labels: n, titleId: r }) {
	let i = e.requestedSchema, a = Mo(i?.properties) ? i.properties : {}, o = Array.isArray(i?.required) ? i.required.filter((e) => typeof e == "string") : [];
	return /* @__PURE__ */ Q("form", {
		className: "paui-interaction paui-form",
		onSubmit: (n) => {
			n.preventDefault();
			let r = n.currentTarget, i = new FormData(r), o = {};
			for (let [e, t] of Object.entries(a)) if (Mo(t)) {
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
		children: [/* @__PURE__ */ Q("div", {
			className: "paui-interaction__icon",
			children: /* @__PURE__ */ Q(is, {})
		}), /* @__PURE__ */ Q("div", {
			className: "paui-interaction__content",
			children: [
				/* @__PURE__ */ Q("strong", {
					id: r,
					children: e.message
				}),
				/* @__PURE__ */ Q("div", {
					className: "paui-fields",
					children: Object.entries(a).map(([e, t]) => Mo(t) ? /* @__PURE__ */ Q(fo, {
						name: e,
						schema: t,
						required: o.includes(e)
					}, e) : null)
				}),
				/* @__PURE__ */ Q("div", {
					className: "paui-interaction__actions",
					children: [/* @__PURE__ */ Q("button", {
						className: "paui-button-primary",
						type: "submit",
						children: n.accept
					}), /* @__PURE__ */ Q("button", {
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
function fo({ name: e, schema: t, required: n }) {
	let r = typeof t.title == "string" ? t.title : e, i = typeof t.description == "string" ? t.description : void 0, a = Array.isArray(t.enum) ? t.enum.filter((e) => typeof e == "string") : [];
	return t.type === "boolean" ? /* @__PURE__ */ Q("label", {
		className: "paui-field paui-field--check",
		children: [/* @__PURE__ */ Q("input", {
			name: e,
			type: "checkbox"
		}), /* @__PURE__ */ Q("span", { children: r })]
	}) : a.length ? /* @__PURE__ */ Q("label", {
		className: "paui-field",
		children: [
			/* @__PURE__ */ Q("span", { children: r }),
			/* @__PURE__ */ Q("select", {
				name: e,
				required: n,
				children: a.map((e) => /* @__PURE__ */ Q("option", { children: e }, e))
			}),
			i ? /* @__PURE__ */ Q("small", { children: i }) : null
		]
	}) : /* @__PURE__ */ Q("label", {
		className: "paui-field",
		children: [
			/* @__PURE__ */ Q("span", { children: r }),
			/* @__PURE__ */ Q("input", {
				name: e,
				required: n,
				type: t.type === "number" || t.type === "integer" ? "number" : "text"
			}),
			i ? /* @__PURE__ */ Q("small", { children: i }) : null
		]
	});
}
function po() {
	let { controller: e, snapshot: t, labels: n, runAction: r } = Da("ChatInteractions");
	return /* @__PURE__ */ Q("section", {
		className: "paui-auth",
		children: [
			/* @__PURE__ */ Q(Zo, {}),
			/* @__PURE__ */ Q("strong", { children: n.authRequired }),
			/* @__PURE__ */ Q("div", { children: t.authMethods.map((t) => /* @__PURE__ */ Q("button", {
				type: "button",
				onClick: () => r(() => e.authenticate(t.id)),
				children: t.name
			}, t.id)) })
		]
	});
}
function mo({ controller: e, snapshot: t, labels: n, onClose: r }) {
	let { ids: i } = Da("ChatHeader"), a = L(null), o = L(null), [s, c] = F(!1), [l, u] = F(), d = ho(t);
	I(() => {
		let e = go(o.current), t = e instanceof HTMLElement ? e : void 0;
		return a.current?.focus(), () => {
			t?.isConnected && t.focus();
		};
	}, []), I(() => {
		t.capabilities.listSessions && !t.sessions && (c(!0), e.listSessions().catch((e) => u(e instanceof Error ? e.message : String(e))).finally(() => c(!1)));
	}, [
		e,
		t.capabilities.listSessions,
		t.sessions
	]), I(() => {
		let e = (e) => {
			if (e.key === "Escape") {
				e.preventDefault(), r();
				return;
			}
			if (e.key !== "Tab") return;
			let t = o.current ? [...o.current.querySelectorAll(yo)].filter((e) => !e.hasAttribute("disabled")) : [], n = t[0], i = t.at(-1);
			if (!n || !i) return;
			let a = go(o.current);
			e.shiftKey && a === n ? (e.preventDefault(), i.focus()) : (!e.shiftKey && a === i || !a || !o.current?.contains(a)) && (e.preventDefault(), n.focus());
		};
		return window.addEventListener("keydown", e), () => window.removeEventListener("keydown", e);
	}, [r]);
	let f = async (t) => {
		c(!0), u(void 0);
		try {
			await e.openSession(t), r();
		} catch (e) {
			u(e instanceof Error ? e.message : String(e));
		} finally {
			c(!1);
		}
	}, p = async (t) => {
		c(!0), u(void 0);
		try {
			await e.listSessions(t);
		} catch (e) {
			u(e instanceof Error ? e.message : String(e));
		} finally {
			c(!1);
		}
	}, m = async (t) => {
		c(!0), u(void 0);
		try {
			await e.closeSession(t);
		} catch (e) {
			u(e instanceof Error ? e.message : String(e));
		} finally {
			c(!1);
		}
	};
	return /* @__PURE__ */ Q("div", {
		className: "paui-drawer-backdrop",
		role: "presentation",
		onMouseDown: (e) => {
			e.target === e.currentTarget && r();
		},
		children: /* @__PURE__ */ Q("aside", {
			ref: o,
			className: "paui-drawer",
			role: "dialog",
			"aria-modal": "true",
			"aria-labelledby": i.sessionsTitle,
			children: [/* @__PURE__ */ Q("header", { children: [/* @__PURE__ */ Q("strong", {
				id: i.sessionsTitle,
				children: n.sessions
			}), /* @__PURE__ */ Q("button", {
				ref: a,
				className: "paui-icon-button",
				type: "button",
				onClick: r,
				children: [/* @__PURE__ */ Q(Io, {}), /* @__PURE__ */ Q("span", {
					className: "paui-sr-only",
					children: n.close
				})]
			})] }), /* @__PURE__ */ Q("div", {
				className: "paui-session-list",
				children: [
					s && !t.sessions ? /* @__PURE__ */ Q("span", {
						className: "paui-muted",
						children: "…"
					}) : null,
					!s && !d.length ? /* @__PURE__ */ Q("span", {
						className: "paui-muted",
						children: n.noSessions
					}) : null,
					d.map((r) => /* @__PURE__ */ Q("div", {
						className: "paui-session",
						"data-active": r.sessionId === t.sessionId || void 0,
						children: [/* @__PURE__ */ Q("button", {
							type: "button",
							disabled: s || r.sessionId === t.sessionId,
							onClick: () => void f(r.sessionId),
							children: [/* @__PURE__ */ Q("strong", { children: r.title ?? n.sessionUntitled }), /* @__PURE__ */ Q("span", {
								className: "paui-session__meta",
								children: [r.loaded ? n.sessionPhase(r.loaded.phase) : Ao(r.updatedAt), r.loaded?.interactionCount ? /* @__PURE__ */ Q("span", { children: n.pendingInteractions(r.loaded.interactionCount) }) : null]
							})]
						}), r.loaded && t.capabilities.closeSession ? /* @__PURE__ */ Q("button", {
							className: "paui-icon-button",
							type: "button",
							disabled: s || r.loaded.phase === "running" || r.loaded.phase === "cancelling" || r.loaded.interactionCount > 0,
							title: n.closeSession,
							onClick: () => void m(r.sessionId),
							children: [/* @__PURE__ */ Q(Io, {}), /* @__PURE__ */ Q("span", {
								className: "paui-sr-only",
								children: n.closeSession
							})]
						}) : t.capabilities.deleteSession && r.sessionId !== t.sessionId ? /* @__PURE__ */ Q("button", {
							className: "paui-icon-button",
							type: "button",
							title: n.deleteSession,
							onClick: () => {
								window.confirm(n.confirmDeleteSession(r.title ?? n.sessionUntitled)) && e.deleteSession(r.sessionId).catch((e) => u(e instanceof Error ? e.message : String(e)));
							},
							children: [/* @__PURE__ */ Q(Lo, {}), /* @__PURE__ */ Q("span", {
								className: "paui-sr-only",
								children: n.deleteSession
							})]
						}) : null]
					}, r.sessionId)),
					t.sessions?.nextCursor ? /* @__PURE__ */ Q("button", {
						className: "paui-load-more",
						type: "button",
						disabled: s,
						onClick: () => void p(t.sessions?.nextCursor),
						children: n.loadMore
					}) : null,
					l ? /* @__PURE__ */ Q("span", {
						className: "paui-error-text",
						role: "alert",
						children: l
					}) : null
				]
			})]
		})
	});
}
function ho(e) {
	let t = new Map((e.sessions?.sessions ?? []).map((e) => [e.sessionId, e])), n = new Set(e.loadedSessions.map((e) => e.sessionId));
	return [...e.loadedSessions.map((e) => ({
		...t.get(e.sessionId),
		...e,
		loaded: e
	})), ...(e.sessions?.sessions ?? []).filter((e) => !n.has(e.sessionId))];
}
function go(e) {
	let t = e?.getRootNode();
	return t instanceof Document || t instanceof ShadowRoot ? t.activeElement : document.activeElement;
}
function _o(e) {
	return (typeof e == "string" ? e : (() => {
		try {
			return JSON.stringify(e, null, 2) ?? String(e);
		} catch {
			return String(e);
		}
	})()).slice(0, 1e5);
}
var vo = new ha({
	gfm: !0,
	breaks: !0
}), yo = "a[href], button, input, select, textarea, [tabindex]:not([tabindex=\"-1\"])", bo = new da();
bo.html = ({ text: e }) => Co(e), bo.image = ({ text: e }) => `<span class="paui-markdown-image-alt">${Co(e)}</span>`, bo.checkbox = ({ checked: e }) => e ? "[x] " : "[ ] ", bo.link = ({ href: e, title: t, tokens: n }) => {
	let r = Co(n.map((e) => e.raw).join(""));
	return wo(e) ? `<a href="${So(e)}" target="_blank" rel="noopener noreferrer"${t ? ` title="${So(t)}"` : ""}>${r}</a>` : r;
}, vo.use({ renderer: bo });
function xo(e) {
	let t = vo.parse(e);
	return Pr.sanitize(t, {
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
function So(e) {
	return Co(e).replaceAll("\"", "&quot;").replaceAll("'", "&#39;");
}
function Co(e) {
	return e.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}
function wo(e) {
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
function To(e) {
	let t = Ca.get(e);
	if (t !== void 0) return t;
	let n = ++wa;
	return Ca.set(e, n), n;
}
function Eo(e) {
	if (e.sessionId) return e.sessionInstanceId ? `${e.sessionId}\u0000${e.sessionInstanceId}` : e.sessionId;
}
function Do(e, t) {
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
function Oo(e) {
	return e.some((e) => e.status === "in_progress") ? "in_progress" : e.length && e.every((e) => e.status === "completed") ? "completed" : "pending";
}
function ko(e) {
	switch (e.type) {
		case "tool": return e.status;
		case "plan": return Oo(e.entries);
		case "terminal": return e.exited ? "completed" : "in_progress";
		case "message": return e.pending ? "pending" : void 0;
		case "unsupported": return "unsupported";
	}
}
function Ao(e) {
	if (!e) return "";
	let t = new Date(e);
	return Number.isNaN(t.valueOf()) ? e : jo.format(t);
}
var jo = new Intl.DateTimeFormat(void 0, {
	month: "short",
	day: "numeric",
	hour: "2-digit",
	minute: "2-digit"
});
function Mo(e) {
	return typeof e == "object" && !!e && !Array.isArray(e);
}
function No({ status: e }) {
	return /* @__PURE__ */ Q("span", {
		className: "paui-status",
		"data-status": e,
		children: e.replaceAll("_", " ")
	});
}
function $({ children: e }) {
	return /* @__PURE__ */ Q("svg", {
		viewBox: "0 0 20 20",
		"aria-hidden": "true",
		focusable: "false",
		children: e
	});
}
var Po = () => /* @__PURE__ */ Q($, { children: /* @__PURE__ */ Q("path", { d: "M3 10a7 7 0 1 0 2-4.9M3 3v4h4M10 6v4l3 2" }) }), Fo = () => /* @__PURE__ */ Q($, { children: /* @__PURE__ */ Q("path", { d: "M4 4h8a3 3 0 0 1 3 3v4a3 3 0 0 1-3 3H8l-4 3v-3a3 3 0 0 1-1-2V7a3 3 0 0 1 3-3M10 7v5M7.5 9.5h5" }) }), Io = () => /* @__PURE__ */ Q($, { children: /* @__PURE__ */ Q("path", { d: "m5 5 10 10M15 5 5 15" }) }), Lo = () => /* @__PURE__ */ Q($, { children: /* @__PURE__ */ Q("path", { d: "M4 6h12M8 3h4l1 3M6 6l1 11h6l1-11M9 9v5M12 9v5" }) }), Ro = () => /* @__PURE__ */ Q("svg", {
	viewBox: "0 0 16 16",
	"aria-hidden": "true",
	focusable: "false",
	children: /* @__PURE__ */ Q("path", {
		d: "M8.3125.9802c.3552.0729.6665.224 0.9502.4521.2245.1807.4676.4256.7168.6748L14.707 6.8347 13.293 8.2487 9 3.9558v11.0859H7V3.9558L2.707 8.2487 1.293 6.8347l4.7275-4.7276c.2492-.2492.4923-.4941.7168-.6748.2393-.1924.5471-.3883.9502-.4521.2098-.0332.4156-.025.625 0Z",
		fill: "currentColor"
	})
}), zo = () => /* @__PURE__ */ Q("svg", {
	viewBox: "0 0 16 16",
	"aria-hidden": "true",
	focusable: "false",
	children: /* @__PURE__ */ Q("rect", {
		x: "3",
		y: "3",
		width: "10",
		height: "10",
		rx: "3",
		fill: "currentColor"
	})
}), Bo = () => /* @__PURE__ */ Q($, { children: /* @__PURE__ */ Q("path", { d: "m5 8 5 5 5-5" }) }), Vo = () => /* @__PURE__ */ Q($, { children: /* @__PURE__ */ Q("path", { d: "m12.5 4.5-5 5 5 5" }) }), Ho = () => /* @__PURE__ */ Q("svg", {
	viewBox: "0 0 14 14",
	"aria-hidden": "true",
	focusable: "false",
	children: /* @__PURE__ */ Q("path", { d: "m4 5.5 3 3 3-3" })
}), Uo = () => /* @__PURE__ */ Q($, { children: /* @__PURE__ */ Q("path", { d: "M12.5 4.2a4 4 0 0 0-5 5L3 13.7 6.3 17l4.5-4.5a4 4 0 0 0 5-5l-2.3 2.3-3.3-3.3 2.3-2.3Z" }) }), Wo = () => /* @__PURE__ */ Q($, { children: [
	/* @__PURE__ */ Q("circle", {
		cx: "10",
		cy: "5",
		r: "2"
	}),
	/* @__PURE__ */ Q("circle", {
		cx: "5",
		cy: "14",
		r: "2"
	}),
	/* @__PURE__ */ Q("circle", {
		cx: "15",
		cy: "14",
		r: "2"
	}),
	/* @__PURE__ */ Q("path", { d: "m8.8 6.7-2.6 5.6M11.2 6.7l2.6 5.6M7 14h6" })
] }), Go = () => /* @__PURE__ */ Q($, { children: /* @__PURE__ */ Q("path", { d: "M5 5h5v5M10 5 4.5 10.5M9 9h6v6H9" }) }), Ko = () => /* @__PURE__ */ Q($, { children: /* @__PURE__ */ Q("path", { d: "M6 5h10M6 10h10M6 15h10M3 5h.01M3 10h.01M3 15h.01" }) }), qo = () => /* @__PURE__ */ Q("svg", {
	className: "paui-think-icon",
	viewBox: "0 0 14 14",
	"aria-hidden": "true",
	focusable: "false",
	children: [/* @__PURE__ */ Q("path", {
		d: "M7.06431 5.93342C7.68763 5.93342 8.19307 6.43904 8.19322 7.06233C8.19322 7.68573 7.68772 8.19123 7.06431 8.19123C6.44099 8.19113 5.9354 7.68567 5.9354 7.06233C5.93555 6.43911 6.44108 5.93353 7.06431 5.93342Z",
		fill: "currentColor"
	}), /* @__PURE__ */ Q("path", {
		fillRule: "evenodd",
		clipRule: "evenodd",
		d: "M8.6815.963693c1.4354-.516674 2.9451-.588864 3.8818.347657.9367.9367.8644 2.44641.3477 3.88184-.1984.55112-.4724 1.12477-.8145 1.7041.4004.64909.7176 1.29289.9395 1.90918.5167 1.43543.5891 2.94513-.3477 3.88183-.9367.9367-2.4463.8644-3.8818.3477-.61628-.2219-1.26009-.5391-1.90918-.9395-.57935.3421-1.15297.616-1.7041.8145-1.43545.5166-2.94512.589-3.88184-.3477-.936521-.9367-.864331-2.4465-.347656-3.88188.208126-.57809.499486-1.18084.865236-1.78907-.30714-.53529-.55661-1.06415-.74024-1.57421C.572068 3.88278.499714 2.37306 1.43638 1.43635c.9367-.936695 2.44642-.864306 3.88184-.34766.51006.18363 1.03893.43311 1.57421.74024.60823-.36575 1.21098-.65712 1.78907-.865237ZM11.3573 8.01154c-.449.61099-.9672 1.21719-1.54787 1.79786-.58066.5807-1.18688 1.0989-1.79785 1.5478.41412.2269.81712.4115 1.20117.5499 1.33285.4797 2.21185.3476 2.62695-.0674.4151-.4151.5472-1.2941.0674-2.62698-.1383-.38406-.323-.78704-.5498-1.20118ZM2.56529 8.02912c-.19185.3641-.35034.71884-.47266 1.0586-.47972 1.33268-.34751 2.21178.06738 2.62698.41504.415 1.29414.5471 2.62696.0674.3236-.1165.66089-.2657 1.00683-.4454-.5448-.4144-1.08458-.8834-1.60351-1.4023-.61451-.61453-1.1586-1.25807-1.625-1.90528Zm4.34179-4.78222c-.66643.45789-1.34248 1.01631-1.99316 1.66699-.65067.65067-1.2091 1.32674-1.66699 1.99316.47981.7262 1.08084 1.46754 1.79199 2.17871.61051.61051 1.24291 1.14074 1.86914 1.58204.68562-.4653 1.38274-1.03704 2.05273-1.70704.67001-.67001 1.24171-1.3671 1.70701-2.05273-.4413-.62623-.97149-1.25863-1.58201-1.86914-.71117-.71116-1.45251-1.31217-2.17871-1.79199Zm4.80762-1.08692c-.4151-.41489-1.2943-.5471-2.62695-.06738-.3394.12219-.69393.28011-1.05762.47168.64715.46637 1.28982 1.01152 1.9043 1.62598.51897.51894.98787 1.0587 1.40237 1.60351.1796-.34592.3288-.68325.4453-1.00683.4797-1.33278.3476-2.21192-.0674-2.62696ZM4.91197 2.2176c-1.33275-.47972-2.21193-.34765-2.62696.06738-.415.41505-.5471 1.29422-.06738 2.62696.09946.27628.22349.56233.36914.85546.43254-.5787.92797-1.1516 1.47852-1.70214.55055-.55056 1.12343-1.04598 1.70214-1.47852-.29312-.14564-.57919-.26968-.85546-.36914Z",
		fill: "currentColor"
	})]
}), Jo = () => /* @__PURE__ */ Q($, { children: /* @__PURE__ */ Q("path", { d: "M5 3h10v14H5zM8 7h4M8 10h4" }) }), Yo = () => /* @__PURE__ */ Q($, { children: [/* @__PURE__ */ Q("circle", {
	cx: "8.5",
	cy: "8.5",
	r: "5.5"
}), /* @__PURE__ */ Q("path", { d: "m12.5 12.5 4 4" })] }), Xo = () => /* @__PURE__ */ Q($, { children: /* @__PURE__ */ Q("path", { d: "m4 6 4 4-4 4M10 14h6" }) }), Zo = () => /* @__PURE__ */ Q($, { children: /* @__PURE__ */ Q("path", { d: "M10 2 16 5v5c0 4-2.5 6.5-6 8-3.5-1.5-6-4-6-8V5l6-3Zm-2 8 1.5 1.5L13 8" }) }), Qo = () => /* @__PURE__ */ Q($, { children: /* @__PURE__ */ Q("path", { d: "M8 12 12 8M6.5 13.5l-1 1a3 3 0 0 1-4-4l3-3a3 3 0 0 1 4 0M13.5 6.5l1-1a3 3 0 0 1 4 4l-3 3a3 3 0 0 1-4 0" }) }), $o = () => /* @__PURE__ */ Q($, { children: /* @__PURE__ */ Q("path", { d: "M5 2h7l4 4v12H5V2Zm7 0v5h4" }) }), es = () => /* @__PURE__ */ Q($, { children: /* @__PURE__ */ Q("path", { d: "M5 3v14M3 5l2-2 2 2M15 17V3M13 15l2 2 2-2M9 7h3M9 13h3" }) }), ts = () => /* @__PURE__ */ Q($, { children: /* @__PURE__ */ Q("path", { d: "M6 5h10v10H6zM3 8v9h9" }) }), ns = () => /* @__PURE__ */ Q($, { children: [/* @__PURE__ */ Q("circle", {
	cx: "10",
	cy: "10",
	r: "7"
}), /* @__PURE__ */ Q("path", { d: "M10 9v5M10 6h.01" })] }), rs = () => /* @__PURE__ */ Q($, { children: /* @__PURE__ */ Q("path", { d: "m10 2 1.5 4.5L16 8l-4.5 1.5L10 14l-1.5-4.5L4 8l4.5-1.5L10 2ZM15.5 13l.7 2.3 2.3.7-2.3.7-.7 2.3-.7-2.3-2.3-.7 2.3-.7.7-2.3Z" }) }), is = () => /* @__PURE__ */ Q($, { children: /* @__PURE__ */ Q("path", { d: "M4 3h12v14H4zM7 7h6M7 10h6M7 13h3" }) }), as = ".pretty-aui-standalone-root{box-sizing:border-box;width:100%;min-width:0;height:100%;min-height:0}.pretty-aui-standalone-root>.pretty-aui{height:100%;min-height:0}.pretty-aui{--paui-default-background:#fff;--paui-default-surface:#f7f8fa;--paui-default-surface-raised:#fff;--paui-default-user-bubble:#edf3fe;--paui-default-text:#0f1115;--paui-default-text-muted:#667085;--paui-default-border:#e5e7eb;--paui-default-accent:#4176e6;--paui-default-on-accent:#fff;--paui-default-accent-soft:#edf3fe;--paui-default-danger:#c63d4f;--paui-default-warning:#a86610;--paui-default-success:#24845b;--paui-default-action-hover:#679efe;--paui-default-flow-title:#61666b;--paui-default-flow-copy:#81858c;--paui-default-flow-caption:#adb2b8;--paui-background:var(--pretty-aui-color-background,var(--paui-default-background));--paui-surface:var(--pretty-aui-color-surface,var(--paui-default-surface));--paui-surface-raised:var(--pretty-aui-color-surface-raised,var(--paui-default-surface-raised));--paui-user-bubble:var(--pretty-aui-color-user-bubble,var(--paui-default-user-bubble));--paui-text:var(--pretty-aui-color-text,var(--paui-default-text));--paui-text-muted:var(--pretty-aui-color-text-muted,var(--paui-default-text-muted));--paui-border:var(--pretty-aui-color-border,var(--paui-default-border));--paui-accent:var(--pretty-aui-color-accent,var(--paui-default-accent));--paui-on-accent:var(--pretty-aui-color-on-accent,var(--paui-default-on-accent));--paui-accent-soft:var(--pretty-aui-color-accent-soft,var(--paui-default-accent-soft));--paui-danger:var(--pretty-aui-color-danger,var(--paui-default-danger));--paui-warning:var(--pretty-aui-color-warning,var(--paui-default-warning));--paui-success:var(--pretty-aui-color-success,var(--paui-default-success));--paui-action-hover:var(--paui-default-action-hover);--paui-flow-title:var(--pretty-aui-color-text-muted,var(--paui-default-flow-title));--paui-flow-copy:var(--pretty-aui-color-text-muted,var(--paui-default-flow-copy));--paui-flow-caption:var(--pretty-aui-color-text-muted,var(--paui-default-flow-caption));--paui-sans:var(--pretty-aui-font-sans,Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif);--paui-mono:var(--pretty-aui-font-mono,ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace);--paui-shadow-raised:var(--pretty-aui-shadow-raised,0 4px 12px 0 #00000005, 0 2px 8px 0 #0000000a);--paui-content-width:var(--pretty-aui-content-max-width,748px);--paui-composer-width:var(--pretty-aui-composer-max-width,780px);--paui-gutter:var(--pretty-aui-gutter,16px);box-sizing:border-box;width:100%;height:var(--pretty-aui-height,680px);min-width:0;min-height:var(--pretty-aui-min-height,420px);border:1px solid var(--paui-border);color:var(--paui-text);--lightningcss-light:initial;--lightningcss-dark: ;color-scheme:light;background:var(--paui-background);contain:layout style;font-family:var(--paui-sans);text-align:left;isolation:isolate;border-radius:14px;flex-direction:column;font-size:14px;line-height:1.5;display:flex;position:relative;overflow:clip;container:pretty-aui/inline-size}.pretty-aui[data-scheme=dark]{--paui-default-background:#151517;--paui-default-surface:#232324;--paui-default-surface-raised:#2c2c2e;--paui-default-user-bubble:#2c2c2e;--paui-default-text:#f9fafb;--paui-default-text-muted:#a4a7ae;--paui-default-border:#343438;--paui-default-accent:#679efe;--paui-default-on-accent:#0f1115;--paui-default-accent-soft:#202c43;--paui-default-danger:#f08a96;--paui-default-warning:#e6ab5e;--paui-default-success:#65c99c;--paui-default-action-hover:#8ab4ff;--paui-default-flow-title:#cfd3d6;--paui-default-flow-copy:#adb2b8;--paui-default-flow-caption:#81858c;--lightningcss-light: ;--lightningcss-dark:initial;color-scheme:dark}@media (prefers-color-scheme:dark){.pretty-aui[data-scheme=system]{--paui-default-background:#151517;--paui-default-surface:#232324;--paui-default-surface-raised:#2c2c2e;--paui-default-user-bubble:#2c2c2e;--paui-default-text:#f9fafb;--paui-default-text-muted:#a4a7ae;--paui-default-border:#343438;--paui-default-accent:#679efe;--paui-default-on-accent:#0f1115;--paui-default-accent-soft:#202c43;--paui-default-danger:#f08a96;--paui-default-warning:#e6ab5e;--paui-default-success:#65c99c;--paui-default-action-hover:#8ab4ff;--paui-default-flow-title:#cfd3d6;--paui-default-flow-copy:#adb2b8;--paui-default-flow-caption:#81858c;--lightningcss-light: ;--lightningcss-dark:initial;color-scheme:dark}}.pretty-aui *,.pretty-aui :before,.pretty-aui :after{box-sizing:border-box}.pretty-aui button,.pretty-aui input,.pretty-aui select,.pretty-aui textarea{color:inherit;font:inherit}.pretty-aui button{cursor:pointer}.pretty-aui :is(button,input,select,textarea):disabled{cursor:not-allowed;opacity:.46}.pretty-aui :is(button,input,select,textarea,summary,a,.paui-body,.paui-context-injection__body):focus-visible{outline:2px solid var(--paui-accent);outline-offset:2px}.pretty-aui svg{fill:none;stroke:currentColor;stroke-linecap:round;stroke-linejoin:round;stroke-width:1.6px;flex:none;width:18px;height:18px}.paui-header{z-index:4;border-bottom:1px solid var(--paui-border);background:color-mix(in srgb, var(--paui-background) 94%, transparent);-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px);justify-content:space-between;align-items:center;min-width:0;min-height:56px;padding:10px 14px 10px 18px;display:flex}.pretty-aui[data-surface=sidebar] .paui-header{min-height:48px;padding:7px 8px 7px 12px}.paui-identity,.paui-header__actions,.paui-interaction__actions,.paui-config{align-items:center;display:flex}.paui-identity{flex:auto;gap:10px;min-width:0}.paui-identity>div{min-width:0;display:grid}.paui-identity strong{letter-spacing:-.01em;text-overflow:ellipsis;white-space:nowrap;font-size:13px;font-weight:600;overflow:hidden}.paui-lineage{min-width:0;display:grid}.paui-lineage__titles{white-space:nowrap;align-items:center;gap:6px;min-width:0;display:flex}.paui-lineage__titles strong{text-overflow:ellipsis;min-width:0;overflow:hidden}.paui-lineage__ancestor{min-width:0;color:var(--paui-flow-caption);align-items:center;gap:6px;display:inline-flex}.paui-lineage__ancestor button{max-width:144px;color:var(--paui-text-muted);text-overflow:ellipsis;white-space:nowrap;background:0 0;border:0;padding:0;font-size:13px;overflow:hidden}.paui-lineage__ancestor button:hover:not(:disabled){color:var(--paui-text)}.paui-lineage__back{background:0 0;border:0;border-radius:7px;place-items:center;width:28px;height:28px;padding:0;display:none}.paui-lineage__back:hover:not(:disabled){background:var(--paui-surface)}.paui-lineage__back svg{width:16px;height:16px}.paui-protocol{color:var(--paui-text-muted);font-family:var(--paui-mono);letter-spacing:.02em;text-overflow:ellipsis;text-transform:uppercase;white-space:nowrap;font-size:10px;overflow:hidden}.pretty-aui[data-surface=sidebar] .paui-protocol{display:none}.paui-presence{border:2px solid var(--paui-background);background:var(--paui-text-muted);width:9px;height:9px;box-shadow:0 0 0 1px var(--paui-border);border-radius:50%;flex:none}.paui-presence[data-phase=idle]{background:var(--paui-success)}.paui-presence:is([data-phase=running],[data-phase=awaiting_user],[data-phase=cancelling]){background:var(--paui-accent);box-shadow:0 0 0 1px var(--paui-accent), 0 0 0 4px var(--paui-accent-soft)}.paui-header__actions{flex:none;gap:2px}.paui-icon-button,.paui-send,.paui-to-bottom{background:0 0;border:0;border-radius:10px;place-items:center;width:34px;height:34px;padding:0;display:inline-grid}.paui-icon-button:hover:not(:disabled){background:var(--paui-surface)}.paui-body{min-width:0;min-height:0;padding:24px var(--paui-gutter) 0;overscroll-behavior:contain;scrollbar-color:var(--paui-border) transparent;scrollbar-gutter:stable;flex:auto;position:relative;overflow:hidden auto}.paui-transcript{width:100%;max-width:var(--paui-content-width);gap:28px;margin:0 auto;padding-bottom:24px;display:grid}.paui-turn{gap:16px;min-width:0;display:grid}.paui-message{min-width:0}.paui-message[data-role=user]{background:var(--paui-user-bubble);border-radius:22px;max-width:min(525px,82%);margin-left:auto;padding:10px 16px}.paui-message[data-role=user][data-pending=true]{opacity:.68}.paui-message__label{display:none}.paui-message__content>:first-child,.paui-markdown>:first-child{margin-top:0}.paui-message__content>:last-child,.paui-markdown>:last-child{margin-bottom:0}.paui-markdown{overflow-wrap:anywhere;min-width:0;font-size:16px;line-height:28px}.paui-message[data-role=user] .paui-markdown{font-size:16px;line-height:24px}.paui-markdown :is(p,ul,ol,pre,blockquote){margin:.72em 0}.paui-markdown :is(h1,h2,h3,h4){letter-spacing:-.015em;margin:1.15em 0 .45em;font-size:1em;font-weight:650}.paui-markdown :is(code),.paui-url,.paui-terminal pre,.paui-diff pre,.paui-resource pre{font-family:var(--paui-mono);font-size:.84em}.paui-markdown :not(pre)>code{background:var(--paui-surface);border-radius:5px;padding:.14em .35em}.paui-markdown pre,.paui-terminal pre,.paui-diff pre,.paui-resource pre{border:1px solid var(--paui-border);background:var(--paui-surface);white-space:pre;border-radius:9px;max-width:100%;padding:12px 14px;line-height:1.55;overflow:auto}.paui-markdown a,.paui-resource{color:var(--paui-accent);-webkit-text-decoration-color:color-mix(in srgb, var(--paui-accent) 45%, transparent);text-decoration-color:color-mix(in srgb, var(--paui-accent) 45%, transparent);text-underline-offset:3px}.paui-activities{gap:16px;min-width:0;display:grid}.paui-activity,.paui-thought,.paui-disclosure,.paui-diff,.paui-resource{min-width:0}.paui-thought>summary,.paui-disclosure>summary,.paui-diff>summary,.paui-resource>summary{min-height:28px;color:var(--paui-text-muted);cursor:pointer;border-radius:6px;align-items:center;gap:7px;font-size:13px;line-height:20px;list-style:none;display:flex}.paui-thought>summary:hover,.paui-disclosure>summary:hover{color:color-mix(in srgb, var(--paui-text) 78%, var(--paui-text-muted))}.pretty-aui summary::-webkit-details-marker{display:none}.paui-thought>summary svg,.paui-disclosure>summary svg,.paui-diff>summary svg,.paui-resource>summary svg{width:15px;height:15px}.paui-thought__body,.paui-disclosure__body{color:var(--paui-text-muted);padding:4px 0 4px 22px;font-size:14px;line-height:24px}.pretty-aui .paui-flow-summary{align-items:center;gap:0;min-width:0;height:24px;min-height:24px;line-height:24px;display:flex;position:relative;overflow:hidden}.paui-flow-leading{width:16px;height:16px;color:var(--paui-flow-copy);flex:none;justify-content:center;align-items:center;margin-right:6px;display:inline-flex;position:relative}.paui-flow-icon,.paui-flow-chevron{justify-content:center;align-items:center;transition:opacity .1s;display:inline-flex}.paui-flow-chevron{opacity:0;position:absolute;inset:0}.pretty-aui .paui-flow-leading svg{width:14px;height:14px}.pretty-aui .paui-flow-leading .paui-think-icon{fill:currentColor;stroke:none}.paui-flow-summary:hover .paui-flow-icon,.paui-thought[open] .paui-flow-icon,.paui-tool[open] .paui-flow-icon,.paui-context-injection[open] .paui-flow-icon{opacity:0}.paui-flow-summary:hover .paui-flow-chevron,.paui-thought[open] .paui-flow-chevron,.paui-tool[open] .paui-flow-chevron,.paui-context-injection[open] .paui-flow-chevron{opacity:1}.paui-flow-title{color:var(--paui-flow-title);flex:none;font-size:14px;font-weight:400;line-height:24px}.paui-flow-separator{background:var(--paui-flow-caption);border-radius:1px;flex:none;width:2px;height:2px;margin:0 8px}.paui-flow-preview{min-width:0;color:var(--paui-flow-copy);text-overflow:ellipsis;white-space:nowrap;flex:auto;font-size:14px;line-height:24px;overflow:hidden}.paui-flow-preview[data-follow-end=true]{text-overflow:clip}.paui-context-injection__body{box-sizing:border-box;width:calc(100% - 22px);max-height:141px;color:var(--paui-text-muted);background:var(--paui-surface);font:400 11px/16px var(--paui-mono);scrollbar-color:var(--paui-border) transparent;border-radius:8px;margin:4px 0 0 22px;padding:10px 12px 12px;overflow:auto}.paui-context-injection__body>*+*{margin-top:8px}.paui-context-block{gap:4px;min-width:0;display:grid}.paui-context-meta{min-width:0;color:var(--paui-text-muted);overflow-wrap:anywhere;flex-wrap:wrap;gap:4px 10px;display:flex}.paui-context-meta>span+span{color:var(--paui-flow-caption)}.paui-context-text{color:var(--paui-flow-copy);font:inherit;overflow-wrap:anywhere;white-space:pre-wrap;margin:0}.paui-context-identifier,.paui-context-truncated{color:var(--paui-flow-caption);overflow-wrap:anywhere}.paui-subagent-row{align-items:flex-start;gap:4px;width:100%;min-width:0;min-height:24px;display:flex}.paui-subagent{flex:auto;min-width:0}.paui-subagent-status{color:var(--paui-flow-caption);white-space:nowrap;flex:none;align-items:center;gap:8px;margin-left:12px;font-size:11px;line-height:24px;display:inline-flex}.paui-subagent-status__ongoing{align-items:center;gap:5px;display:inline-flex}.paui-subagent-status__spinner{border:1.5px solid color-mix(in srgb, var(--paui-accent) 28%, transparent);border-top-color:var(--paui-accent);border-radius:50%;width:9px;height:9px;animation:.8s linear infinite paui-subagent-spin}.paui-subagent-status[data-status=failed],.paui-subagent-status[data-status=cancelled],.paui-subagent:is([data-state=failed],[data-state=cancelled]) .paui-flow-leading{color:var(--paui-danger)}.paui-subagent-open{width:24px;height:24px;color:var(--paui-flow-copy);background:0 0;border:0;border-radius:6px;flex:none;place-items:center;padding:0;display:inline-grid}.paui-subagent-open:hover:not(:disabled){color:var(--paui-text);background:var(--paui-surface)}.paui-subagent-open svg{width:14px;height:14px}.paui-subagent[open] .paui-flow-icon{opacity:0}.paui-subagent[open] .paui-flow-chevron{opacity:1}@keyframes paui-subagent-spin{to{transform:rotate(360deg)}}.paui-thought[open] .paui-flow-separator,.paui-thought[open] .paui-flow-preview{display:none}.paui-tool[data-state=failed] .paui-flow-leading{color:var(--paui-danger)}.paui-thought[data-running=true]>.paui-flow-summary:after,.paui-tool:is([data-state=pending],[data-state=in_progress])>.paui-flow-summary:after{inset-block:0;background:linear-gradient(90deg, transparent 0%, color-mix(in srgb, var(--paui-background) 60%, transparent) 55%, transparent 100%);content:\"\";pointer-events:none;width:300px;animation:2.6s ease-out infinite paui-flow-sweep;position:absolute;left:0}@keyframes paui-flow-sweep{0%{left:-300px}90%,to{left:100%}}@media (prefers-reduced-motion:reduce){.paui-thought[data-running=true]>.paui-flow-summary:after,.paui-tool:is([data-state=pending],[data-state=in_progress])>.paui-flow-summary:after{animation:none}.paui-subagent-status__spinner{border-color:var(--paui-accent);background:var(--paui-accent);animation:none}}.paui-status{color:var(--paui-text-muted);font-family:var(--paui-mono);letter-spacing:.04em;text-transform:uppercase;margin-left:auto;font-size:9px}.paui-status:is([data-status=failed],[data-status=cancelled]){color:var(--paui-danger)}.paui-plan__list{gap:6px;margin:4px 0 0;padding:4px 0 4px 22px;list-style:none;display:grid}.paui-plan__list li{color:var(--paui-text-muted);grid-template-columns:12px 1fr;align-items:start;gap:8px;font-size:13px;line-height:20px;display:grid}.paui-plan__mark{border:1px solid;border-radius:50%;width:7px;height:7px;margin-top:6px}.paui-plan__list li[data-status=completed] .paui-plan__mark{border-color:var(--paui-success);background:var(--paui-success)}.paui-plan__list li[data-status=in_progress]{color:var(--paui-text)}.paui-plan__list li[data-status=in_progress] .paui-plan__mark{border-color:var(--paui-accent);background:var(--paui-accent);box-shadow:inset 0 0 0 2px var(--paui-background)}.paui-media{border-radius:10px;max-width:100%;max-height:420px;margin:10px 0;display:block}.paui-resource{align-items:center;gap:6px;display:inline-flex}.paui-resource svg{width:15px;height:15px}.paui-unsupported,.paui-muted{color:var(--paui-text-muted);font-size:12px}.paui-notice{background:var(--paui-accent-soft);border-radius:9px;align-items:center;gap:10px;padding:10px 12px;display:flex}.paui-notice>div,.paui-error>div{flex:1;min-width:0;display:grid}.paui-notice strong,.paui-error strong{font-size:12px}.paui-notice span,.paui-error span{color:var(--paui-text-muted);font-size:11px}.paui-notice svg,.paui-error svg{width:16px}.paui-empty{max-width:340px;color:var(--paui-text-muted);text-align:center;justify-items:center;margin:clamp(42px,12vh,90px) auto;display:grid}.paui-empty svg{width:24px;height:24px;color:var(--paui-accent);margin-bottom:12px}.paui-empty strong{color:var(--paui-text);letter-spacing:-.01em;font-size:16px;font-weight:600}.paui-empty p{margin:5px 0 0;font-size:12px}.paui-interactions{z-index:3;min-width:0;padding:0 var(--paui-gutter);background:var(--paui-background);gap:8px;display:grid}.paui-interactions:empty{display:none}.paui-error,.paui-interaction,.paui-auth{width:100%;max-width:var(--paui-content-width);border:1px solid var(--paui-border);background:var(--paui-surface);border-radius:12px;gap:11px;margin:0 auto;display:flex}.paui-error{border-color:color-mix(in srgb, var(--paui-danger) 30%, var(--paui-border));align-items:center;padding:10px 12px}.paui-error button,.paui-auth button,.paui-load-more{border:1px solid var(--paui-border);background:var(--paui-background);border-radius:8px;padding:6px 10px;font-size:12px}.paui-interaction{padding:14px}.paui-interaction__icon{width:28px;height:28px;color:var(--paui-accent);background:var(--paui-accent-soft);border-radius:8px;flex:none;place-items:center;display:grid}.paui-interaction__icon svg{width:16px}.paui-interaction__content{flex:1;gap:8px;min-width:0;display:grid}.paui-interaction__content>strong{font-size:13px}.paui-interaction__content>p{color:var(--paui-text-muted);margin:-3px 0 0;font-size:12px}.paui-interaction__actions{flex-wrap:wrap;gap:6px}.paui-button-primary,.paui-button-secondary,.paui-button-ghost{border-radius:8px;min-height:30px;padding:5px 10px;font-size:12px}.paui-button-primary{border:1px solid var(--paui-accent);color:var(--paui-on-accent);background:var(--paui-accent)}.paui-button-secondary{border:1px solid var(--paui-border);background:var(--paui-background)}.paui-button-ghost{color:var(--paui-text-muted);background:0 0;border:1px solid #0000}.paui-url{border:1px solid var(--paui-border);background:var(--paui-background);text-overflow:ellipsis;white-space:nowrap;border-radius:7px;padding:7px 8px;overflow:hidden}.paui-fields{gap:10px;display:grid}.paui-field{color:var(--paui-text-muted);gap:4px;font-size:11px;display:grid}.paui-field input,.paui-field select{border:1px solid var(--paui-border);min-height:34px;color:var(--paui-text);background:var(--paui-background);border-radius:7px;padding:6px 8px}.paui-field small{font-size:10px}.paui-field--check{align-items:center;display:flex}.paui-auth{justify-items:start;padding:16px;display:grid}.paui-auth>div{gap:6px;display:flex}.paui-auth>svg{color:var(--paui-accent)}.paui-composer-wrap{z-index:3;width:100%;padding:36px var(--paui-gutter) 8px;background:linear-gradient(to bottom, color-mix(in srgb, var(--paui-background) 0%, transparent) 0, var(--paui-background) 36px);justify-items:center;gap:6px;display:grid}.paui-composer-wrap[data-placement=hero]{transition:top .18s,transform .18s;position:absolute;top:50%;left:0;transform:translateY(-10%)}.paui-composer{width:100%;max-width:var(--paui-composer-width);border:1px solid var(--paui-border);background:var(--paui-surface-raised);box-shadow:var(--paui-shadow-raised);border-radius:22px;flex-direction:column;gap:12px;padding:10px 8px 6px 16px;font-size:16px;line-height:24px;transition:border-color .12s,box-shadow .12s;display:flex;position:relative}.paui-composer:focus-within{border-color:color-mix(in srgb, var(--paui-accent) 55%, var(--paui-border))}.paui-composer__context{scrollbar-width:thin;flex-wrap:wrap;align-items:center;gap:6px;min-width:0;max-height:68px;padding-right:4px;display:flex;overflow-y:auto}.pretty-aui .paui-context-add{width:22px;height:22px;color:var(--paui-text-muted);background:0 0;border:0;border-radius:6px;flex:0 0 22px;place-items:center;padding:0;font-size:17px;line-height:1;display:inline-grid}.pretty-aui .paui-context-add:hover:not(:disabled){color:var(--paui-text);background:var(--paui-surface)}.paui-context-chip{border:1px solid var(--paui-border);min-width:0;max-width:min(260px,100% - 28px);color:var(--paui-text);background:var(--paui-background);border-radius:7px;align-items:center;gap:4px;padding:2px 3px 2px 8px;font-size:11px;line-height:18px;display:inline-flex}.paui-context-chip__label{text-overflow:ellipsis;white-space:nowrap;overflow:hidden}.pretty-aui .paui-context-chip button{width:18px;height:18px;color:var(--paui-text-muted);background:0 0;border:0;border-radius:5px;flex:0 0 18px;place-items:center;padding:0;font-size:14px;line-height:1;display:inline-grid}.pretty-aui .paui-context-chip button:hover:not(:disabled){color:var(--paui-text);background:var(--paui-surface)}.paui-composer textarea{resize:none;background:0 0;border:0;outline:0;width:100%;min-height:24px;max-height:336px;padding:2px 0;line-height:24px;overflow-y:auto}.pretty-aui .paui-composer textarea:focus-visible{outline:0}.paui-composer-wrap[data-placement=hero] .paui-composer textarea{min-height:52px}.paui-composer textarea::placeholder{color:var(--paui-text-muted)}.paui-composer__actions{justify-content:space-between;align-items:center;width:100%;min-width:0;display:flex}.pretty-aui .paui-send{color:var(--paui-on-accent);background:var(--paui-accent);border-radius:999px;transition:background-color .1s;transform:translateY(-2px)}.pretty-aui .paui-send:hover:not(:disabled){background:var(--paui-action-hover)}.pretty-aui .paui-send:disabled{opacity:.4}.pretty-aui .paui-send svg{stroke:none;width:16px;height:16px}.pretty-aui .paui-stop{color:#fff;background:var(--paui-accent)}.paui-config{width:auto;min-height:20px;color:var(--paui-text-muted);gap:8px;font-size:10px}.paui-config label{align-items:center;gap:4px;display:inline-flex}.paui-config select{max-width:150px;color:var(--paui-text-muted);background:0 0;border:0;font-size:10px}.paui-commands{right:var(--paui-gutter);bottom:76px;left:var(--paui-gutter);max-width:var(--paui-composer-width);border:1px solid var(--paui-border);background:var(--paui-surface-raised);box-shadow:var(--paui-shadow-raised);border-radius:12px;margin:0 auto;display:grid;position:absolute;overflow:hidden}.paui-commands button{border:0;border-bottom:1px solid var(--paui-border);text-align:left;background:0 0;grid-template-columns:minmax(110px,auto) 1fr;gap:10px;padding:8px 10px;display:grid}.paui-commands button:hover{background:var(--paui-surface)}.paui-commands code{color:var(--paui-accent);font-family:var(--paui-mono);font-size:11px}.paui-commands span{color:var(--paui-text-muted);font-size:11px}.paui-to-bottom{border:1px solid var(--paui-border);background:var(--paui-surface-raised);box-shadow:var(--paui-shadow-raised);border-radius:50%}.paui-to-bottom-row{flex:none;place-items:center;height:46px;display:grid}.paui-drawer-backdrop{z-index:20;background:0 0;justify-content:flex-end;display:flex;position:absolute;inset:0}.paui-drawer{border-left:1px solid var(--paui-border);background:var(--paui-background);width:min(340px,88%);height:100%;min-height:0;box-shadow:var(--paui-shadow-raised);grid-template-rows:auto minmax(0,1fr);display:grid}.paui-drawer>header{border-bottom:1px solid var(--paui-border);justify-content:space-between;align-items:center;min-height:56px;padding:10px 12px 10px 16px;display:flex}.paui-session-list{overscroll-behavior:contain;scrollbar-color:var(--paui-border) transparent;scrollbar-gutter:stable;align-content:start;gap:2px;min-height:0;padding:8px;display:grid;overflow-y:auto}.paui-session{border-radius:9px;grid-template-columns:minmax(0,1fr) auto;align-items:center;display:grid}.paui-session[data-active=true]{background:var(--paui-accent-soft)}.paui-session>button:first-child{text-align:left;background:0 0;border:0;min-width:0;padding:9px 8px;display:grid}.paui-session>button:first-child strong{text-overflow:ellipsis;white-space:nowrap;font-size:12px;overflow:hidden}.paui-session>button:first-child span{color:var(--paui-text-muted);font-size:10px}.paui-session__meta{align-items:center;gap:6px;min-width:0;display:flex}.paui-session__meta>span:before{content:\"·\";margin-right:6px}.paui-usage{max-width:156px;color:var(--paui-text-muted);font-family:var(--paui-mono);text-overflow:ellipsis;white-space:nowrap;font-size:10px;overflow:hidden}.paui-tool-raw{gap:12px;display:grid}.paui-tool-raw section{gap:4px;display:grid}.paui-tool-raw strong{color:var(--paui-text-muted);text-transform:uppercase;font-size:10px}.paui-tool-raw pre{max-height:280px;overflow:auto}.paui-load-more{margin-top:6px}.paui-error-text{color:var(--paui-danger);padding:8px;font-size:11px}.paui-sr-only{clip:rect(0, 0, 0, 0);white-space:nowrap;border:0;width:1px;height:1px;padding:0;position:absolute;overflow:hidden}@container pretty-aui (width<=560px){.paui-header{min-height:48px;padding:7px 8px 7px 12px}.paui-identity--child{gap:4px}.paui-identity--child .paui-presence,.paui-lineage__ancestor{display:none}.paui-lineage{align-items:center;display:flex}.paui-lineage__back{display:inline-grid}.paui-lineage__titles{flex:auto;min-width:0}.paui-body{padding-top:18px}.paui-transcript{padding-bottom:18px}.paui-message[data-role=user]{max-width:88%}.paui-markdown{font-size:15px;line-height:25px}.paui-message[data-role=user] .paui-markdown{font-size:15px;line-height:23px}.paui-interaction__actions{align-items:stretch}.paui-button-primary,.paui-button-secondary,.paui-button-ghost{flex:auto}.paui-composer-wrap{padding-left:10px;padding-right:10px}.paui-composer{padding-left:14px}}.pretty-aui[data-surface=sidebar] .paui-identity--child{gap:4px}.pretty-aui[data-surface=sidebar] :is(.paui-identity--child .paui-presence,.paui-lineage__ancestor){display:none}.pretty-aui[data-surface=sidebar] .paui-lineage{align-items:center;display:flex}.pretty-aui[data-surface=sidebar] .paui-lineage__back{display:inline-grid}@container pretty-aui (width<=380px){.paui-identity{gap:7px}.paui-protocol{display:none}.paui-message[data-role=user]{max-width:92%}.paui-interaction{padding:11px}.paui-interaction__icon{display:none}}@media (prefers-reduced-motion:reduce){.pretty-aui *,.pretty-aui :before,.pretty-aui :after{scroll-behavior:auto!important;transition-duration:.01ms!important;animation-duration:.01ms!important;animation-iteration-count:1!important}}", os = "Acp-Connection-Id", ss = "Acp-Session-Id", cs = "text/event-stream", ls = "application/json";
r.session_cancel, r.session_close, r.session_delete, r.session_fork, r.session_load, r.session_prompt, r.session_resume, r.session_set_config_option, r.session_set_mode, r.nes_suggest, r.nes_accept, r.nes_reject, r.nes_close, r.document_did_open, r.document_did_change, r.document_did_close, r.document_did_save, r.document_did_focus;
function us(e) {
	if (!n(e)) return;
	let t = e.sessionId;
	return typeof t == "string" ? t : void 0;
}
function ds(e) {
	return "method" in e ? us(e.params) : void 0;
}
function fs(t) {
	if (!e(t) || !("result" in t) || !n(t.result)) return;
	let r = t.result.sessionId;
	return typeof r == "string" ? r : void 0;
}
function ps(e) {
	return e.jsonrpc === "2.0" && "id" in e && "method" in e && e.method === r.initialize;
}
function ms(e) {
	if (typeof e == "string") return `string:${e}`;
	if (typeof e == "number") return `number:${e}`;
	if (e === null) return "null";
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/cookie-store.js
var hs = class {
	cookies = /* @__PURE__ */ new Map();
	store(e) {
		for (let t of gs(e)) {
			let e = vs(t);
			e && this.cookies.set(e.name, e.value);
		}
	}
	apply(e) {
		let t = ys(this.cookieHeader(), e.get("Cookie"));
		t && e.set("Cookie", t);
	}
	clear() {
		this.cookies.clear();
	}
	cookieHeader() {
		return this.cookies.size === 0 ? void 0 : Array.from(this.cookies).map(([e, t]) => `${e}=${t}`).join("; ");
	}
};
function gs(e) {
	let t = e.getSetCookie;
	if (typeof t == "function") return t.call(e).flatMap(_s);
	let n = e.get("Set-Cookie");
	return n ? _s(n) : [];
}
function _s(e) {
	return e.split(/,(?=\s*[^;,\s]+=)/).map((e) => e.trim()).filter((e) => e.length > 0);
}
function vs(e) {
	let t = e.split(";", 1)[0], n = t.indexOf("=");
	if (n <= 0) return;
	let r = t.slice(0, n).trim();
	if (r) return {
		name: r,
		value: t.slice(n + 1).trim()
	};
}
function ys(e, t) {
	let n = /* @__PURE__ */ new Map();
	for (let t of bs(e)) n.set(t.name, t.value);
	for (let e of bs(t ?? void 0)) n.set(e.name, e.value);
	return n.size === 0 ? void 0 : Array.from(n).map(([e, t]) => `${e}=${t}`).join("; ");
}
function bs(e) {
	return e ? e.split(";").map(xs).filter((e) => e !== void 0) : [];
}
function xs(e) {
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
async function* Ss(e) {
	let t = new TextDecoder(), n = e.getReader(), r = new zt(), i = [], a = (e) => {
		let n = t.decode(e);
		return n.endsWith("\r") ? n.slice(0, -1) : n;
	}, o = () => {
		if (i.length === 0) return;
		let e = i;
		return i = [], Cs(e);
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
function Cs(e) {
	let t = e.filter((e) => e.startsWith("data:")).map((e) => {
		let t = e.slice(5);
		return t.startsWith(" ") ? t.slice(1) : t;
	});
	if (t.length === 0) return;
	let r = t.join("\n");
	if (r.trim()) try {
		let e = JSON.parse(r);
		if (n(e) || Array.isArray(e)) return e;
		console.warn("Skipping SSE payload that is not an object or array");
		return;
	} catch (e) {
		console.warn("Failed to parse SSE JSON payload:", e);
		return;
	}
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/http-stream.js
function ws(e, t = {}) {
	return new Ts(e, t).stream;
}
var Ts = class {
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
		this.serverUrl = e, this.fetchImpl = Es(t.fetch), this.headers = t.headers ?? {}, this.cookiePolicy = t.cookies ?? "include", this.cookieStore = t.cookieStore ?? new hs(), this.ownsCookieStore = t.cookieStore === void 0, this.stream = {
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
			if (!ps(t)) throw Error("ACP HTTP stream first message must be initialize");
			let r = await this.fetchRequest({
				method: "POST",
				headers: { "Content-Type": ls },
				body: JSON.stringify(t),
				signal: this.abortController.signal
			});
			if (!r.ok) throw await Ds("ACP initialize failed", r);
			let i = r.headers.get(os);
			if (!i) throw Error("ACP initialize response missing Acp-Connection-Id");
			n = i, this.throwIfClosedDuringInitialize();
			let a = await r.json();
			if (this.throwIfClosedDuringInitialize(), !e(a)) throw Error("ACP initialize response was not a JSON-RPC response");
			if (ms(a.id) !== ("id" in t ? ms(t.id) : void 0)) throw Error("ACP initialize response id did not match initialize request");
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
		let r = n && "method" in e && "id" in e ? ms(e.id) : void 0;
		n && r && this.pendingSessionRequests.set(r, n);
		try {
			let r = await this.fetchRequest({
				method: "POST",
				headers: {
					"Content-Type": ls,
					[os]: t,
					...n ? { [ss]: n } : {}
				},
				body: JSON.stringify(e),
				signal: this.abortController.signal
			});
			if (!r.ok) throw await Ds("ACP POST failed", r);
			if (!("method" in e) && "id" in e) {
				let t = ms(e.id);
				t && this.pendingResponseSessions.delete(t);
			}
		} catch (e) {
			throw r && this.pendingSessionRequests.delete(r), this.errorReadable(e), e;
		}
	}
	sessionIdForOutboundMessage(e) {
		let t = ds(e);
		if (t) return t;
		if (!("id" in e) || "method" in e) return;
		let n = ms(e.id);
		return n ? this.pendingResponseSessions.get(n) : void 0;
	}
	openConnectionSse() {
		let e = this.connectionId;
		e && this.openSse({ [os]: e });
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
			[os]: n,
			[ss]: e
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
		let n = e[ss];
		try {
			let r = await this.fetchRequest({
				method: "GET",
				headers: {
					Accept: cs,
					...e
				},
				signal: this.abortController.signal
			});
			if (!r.ok) throw await Ds("ACP SSE connection failed", r);
			if (!r.body) throw Error("ACP SSE response missing body");
			t.onOpen?.();
			for await (let t of Ss(r.body)) {
				if (this.isClosed) return;
				if (Array.isArray(t)) throw TypeError("ACP HTTP transport does not support JSON-RPC batch messages");
				let n = fs(t);
				n && this.openSessionSse(n), this.trackServerRequestRoute(t, e[ss]), this.trackInboundResponse(t), this.enqueue(t);
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
		let n = ms(e.id);
		n && this.pendingResponseSessions.set(n, t);
	}
	trackInboundResponse(t) {
		if (!e(t)) return;
		let n = ms(t.id);
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
			headers: { [os]: e }
		});
		if (!t.ok) throw await Ds("ACP DELETE failed", t);
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
function Es(e) {
	if (e) return e;
	if (typeof globalThis.fetch == "function") return (e, t) => globalThis.fetch(e, t);
	throw Error("createHttpStream requires globalThis.fetch or options.fetch");
}
async function Ds(e, t) {
	let n = await t.text().catch(() => "");
	return Error(n ? `${e}: ${t.status} ${t.statusText}: ${n}` : `${e}: ${t.status} ${t.statusText}`);
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/ws-utils.js
function Os(e, t, n) {
	if (e.on) {
		let r = (...e) => {
			n(...As(t, e));
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
function ks(e) {
	let t = Ms(e);
	if (typeof t == "string") return t;
}
function As(e, t) {
	return e !== "message" || typeof t[1] != "boolean" ? t : t[1] ? [void 0] : [js(t[0])];
}
function js(e) {
	if (typeof e == "string") return e;
	if (e instanceof ArrayBuffer || ArrayBuffer.isView(e)) return new TextDecoder().decode(e);
	if (Ps(e)) return Fs(e);
}
function Ms(e) {
	let [t] = e;
	return Ns(t) ? t.data : t;
}
function Ns(e) {
	return typeof e == "object" && !!e && "data" in e;
}
function Ps(e) {
	return Array.isArray(e) && e.every(ArrayBuffer.isView);
}
function Fs(e) {
	let t = e.reduce((e, t) => e + t.byteLength, 0), n = new Uint8Array(t), r = 0;
	for (let t of e) n.set(new Uint8Array(t.buffer, t.byteOffset, t.byteLength), r), r += t.byteLength;
	return new TextDecoder().decode(n);
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/ws-stream.js
var Is = 1;
function Ls(e, t = {}) {
	return new Rs(e, t).stream;
}
var Rs = class {
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
		let n = Us(t.WebSocket), r = t.cookies ?? "include";
		this.cookieStore = t.cookieStore ?? new hs(), this.ownsCookieStore = t.cookieStore === void 0, this.socket = new n(e, t.protocols, { headers: zs(t.headers, r, this.cookieStore) }), this.openPromise = new Promise((e, t) => {
			this.resolveOpen = e, this.rejectOpen = t;
		}), this.openPromise.catch(() => void 0), this.detachListeners.push(Os(this.socket, "open", () => {
			this.resolveOpen?.(), this.resolveOpen = void 0, this.rejectOpen = void 0, this.openPromise = void 0;
		})), this.detachListeners.push(Os(this.socket, "message", (...e) => {
			this.handleSocketMessage(e);
		})), this.detachListeners.push(Os(this.socket, "close", () => {
			this.closeReadable();
		})), this.detachListeners.push(Os(this.socket, "error", (e) => {
			this.errorReadable(e);
		})), r === "include" && this.detachListeners.push(Os(this.socket, "upgrade", (e) => {
			let t = Vs(e);
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
		this.socket.readyState !== void 0 && this.socket.readyState !== Is && await this.openPromise;
	}
	handleSocketMessage(e) {
		if (this.isClosed) return;
		let t = ks(e);
		if (t === void 0) return;
		let r;
		try {
			r = JSON.parse(t);
		} catch {
			this.sendProtocolError(ee.parseError());
			return;
		}
		if (!n(r) && !Array.isArray(r)) {
			this.sendProtocolError(ee.invalidRequest(r));
			return;
		}
		this.readableController?.enqueue(r);
	}
	sendProtocolError(e) {
		this.queueMessage(S(e)).catch((e) => {
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
function zs(e, t, n) {
	let r = e ? { ...e } : {};
	if (t === "include") {
		let t = new Headers(e);
		n.apply(t);
		let i = t.get("Cookie");
		i && (r[Bs(r, "Cookie") ?? "Cookie"] = i);
	}
	return Object.keys(r).length > 0 ? r : void 0;
}
function Bs(e, t) {
	return Object.keys(e).find((e) => e.toLowerCase() === t.toLowerCase());
}
function Vs(e) {
	if (e instanceof Headers) return e;
	if (!(!n(e) || !("headers" in e))) return Hs(e.headers);
}
function Hs(e) {
	if (e instanceof Headers) return e;
	if (!n(e)) return;
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
function Us(e) {
	if (e) return e;
	if (typeof globalThis.WebSocket == "function") return globalThis.WebSocket;
	throw Error("createWebSocketStream requires globalThis.WebSocket or options.WebSocket");
}
//#endregion
//#region src/core/transport.ts
function Ws(e, t = {}) {
	let n = Ks(e, t.fetch ?? globalThis.fetch);
	return { open({ signal: r }) {
		return qs(ws(e, {
			fetch: n,
			...t.headers ? { headers: { ...t.headers } } : {},
			...t.cookies ? { cookies: t.cookies } : {}
		}), r);
	} };
}
function Gs(e, t = {}) {
	return { open({ signal: n }) {
		return qs(Ls(e, {
			protocols: [...t.protocols ?? []],
			...t.headers ? { headers: { ...t.headers } } : {},
			...t.cookies ? { cookies: t.cookies } : {},
			...t.WebSocket ? { WebSocket: t.WebSocket } : {}
		}), n);
	} };
}
function Ks(e, t) {
	if (!t) throw new i("INVALID_CONFIGURATION", "Streamable HTTP requires a fetch implementation", { phase: "transport/http" });
	let n = Js(e);
	return async (e, r) => {
		let a = Ys(e, n);
		for (let o = 0; o <= 5; o += 1) {
			let s = await t(e, {
				...r,
				redirect: "manual"
			});
			if (s.type === "opaqueredirect") throw new i("INVALID_CONFIGURATION", "ACP HTTP redirects are opaque in browsers; configure a redirect-free endpoint", { phase: "transport/redirect" });
			if (!Xs(s.status)) return s;
			let c = s.headers.get("location");
			if (!c) return s;
			let l = new URL(c, a);
			if (l.origin !== n.origin) throw new i("INVALID_CONFIGURATION", `ACP HTTP redirect crossed an origin boundary: ${l.origin}`, { phase: "transport/redirect" });
			if (o === 5) throw new i("INVALID_CONFIGURATION", "ACP HTTP exceeded the redirect limit", { phase: "transport/redirect" });
			e = l.href, a = l;
		}
		throw Error("Unreachable redirect state");
	};
}
function qs(e, t) {
	let n = e.readable.getReader(), r = e.writable.getWriter(), a, o = !1, s = (e) => {
		if (!o) {
			o = !0, t.removeEventListener("abort", c);
			try {
				a?.error(e);
			} catch {}
			r.abort(e).catch(() => n.cancel(e)).catch(() => void 0);
		}
	}, c = () => s(t.reason);
	return t.addEventListener("abort", c, { once: !0 }), {
		readable: new ReadableStream({
			start(e) {
				a = e, t.aborted && s(t.reason);
			},
			async pull(e) {
				if (o) return;
				let r = await n.read();
				if (r.done) {
					o = !0, t.removeEventListener("abort", c), e.close();
					return;
				}
				if (!en(r.value)) {
					s(new i("PROTOCOL_VIOLATION", "ACP wire message exceeded the 2 MiB decoded input limit", { phase: "transport/input" }));
					return;
				}
				e.enqueue(r.value);
			},
			cancel(e) {
				s(e);
			}
		}),
		writable: new WritableStream({
			write(e) {
				if (o) throw Error("ACP transport lifetime has ended");
				if (!en(e)) throw new i("PROTOCOL_VIOLATION", "ACP wire message exceeded the 2 MiB decoded output limit", { phase: "transport/output" });
				return r.write(e);
			},
			async close() {
				o || (o = !0, t.removeEventListener("abort", c), await r.close());
			},
			abort(e) {
				s(e);
			}
		})
	};
}
function Js(e) {
	try {
		return new URL(e, globalThis.location === void 0 ? void 0 : globalThis.location.href);
	} catch (t) {
		throw new i("INVALID_CONFIGURATION", `ACP HTTP endpoint must be an absolute URL: ${e}`, {
			cause: t,
			phase: "transport/http"
		});
	}
}
function Ys(e, t) {
	return typeof e == "string" ? new URL(e, t) : e instanceof URL ? e : new URL(e.url, t);
}
function Xs(e) {
	return e >= 300 && e <= 399;
}
//#endregion
//#region src/standalone.tsx
var Zs = 1048576, Qs = 256, $s = /^[A-Za-z0-9+/_-]+={0,2}$/, ec = /* @__PURE__ */ new WeakMap(), tc = /* @__PURE__ */ new WeakMap();
function nc(e, t) {
	if (ec.has(e)) throw Error("pretty-aui: this target is already mounted");
	let n = Object.hasOwn(t, "options");
	if (n === Object.hasOwn(t, "controller")) throw TypeError("pretty-aui: mountChat requires exactly one of options or controller");
	t.styleNonce !== void 0 && rc(t.styleNonce);
	let r = tc.get(e);
	if (e.shadowRoot && e.shadowRoot !== r) throw Error("pretty-aui: mountChat requires a target without an existing shadow root");
	let i = r ?? e.attachShadow({ mode: "open" });
	tc.set(e, i);
	let a = document.createElement("style");
	t.styleNonce !== void 0 && (a.nonce = t.styleNonce), a.textContent = as;
	let o = document.createElement("div");
	o.className = "pretty-aui-standalone-root", i.append(a, o);
	let s = {
		shadow: i,
		style: a,
		container: o
	};
	ec.set(e, s);
	let { surface: c, colorScheme: l, labels: u } = t, d = n ? rn(t.options) : t.controller, f = Lt(o);
	f.render(/* @__PURE__ */ Q(Oa, {
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
					ec.get(e) === s && (a.remove(), o.remove(), ec.delete(e));
				}
			}
		}
	};
	return typeof MutationObserver < "u" && (m = oc(e, () => void h())), {
		controller: d,
		ready: d.ready,
		setDraft(e, t) {
			if (ic(p), e.length > Zs) throw RangeError(`pretty-aui: draft exceeds ${Zs} characters`);
			let n = ac(i);
			(Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")?.set)?.call(n, e), n.dispatchEvent(new Event("input", { bubbles: !0 })), t?.focus && n.focus();
		},
		focusComposer() {
			ic(p), ac(i).focus();
		},
		unmount: h
	};
}
function rc(e) {
	if (e.length === 0 || e.length > Qs || !$s.test(e)) throw TypeError("pretty-aui: styleNonce is not a valid CSP nonce");
}
function ic(e) {
	if (e) throw Error("pretty-aui: mount has been unmounted");
}
function ac(e) {
	let t = e.querySelector("[data-pretty-aui-slot=\"composer-input\"] textarea");
	if (!t) throw Error("pretty-aui: composer is not mounted yet");
	return t;
}
function oc(e, t) {
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
export { i as PrettyAuiError, rn as createChat, Ws as createStreamableHttpConnector, Gs as createWebSocketConnector, nc as mountChat };

//# sourceMappingURL=pretty-aui.js.map