globalThis.__zod_globalConfig ??= {}, globalThis.__zod_globalConfig.jitless = !0;
import { B as e, G as t, H as n, I as r, J as i, K as a, U as o, V as s, W as c, X as l, Y as u, _ as d, a as f, c as p, g as m, h, i as g, l as _, m as v, n as y, o as b, q as x, r as S, s as C, t as w, u as T, z as E } from "./chunks/interactions.js";
//#region node_modules/.pnpm/preact@10.29.8/node_modules/preact/dist/preact.module.js
var ee, D, te, O, ne, re, ie, ae, oe, se, ce, le, k, ue, de, fe = {}, pe = [], me = /acit|ex(?:s|g|n|p|$)|rph|grid|ows|mnc|ntw|ine[ch]|zoo|^ord|itera/i, he = Array.isArray;
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
	if (arguments.length > 2 && (o.children = arguments.length > 3 ? ee.call(arguments, 2) : n), typeof e == "function" && e.defaultProps != null) for (a in e.defaultProps) o[a] === void 0 && (o[a] = e.defaultProps[a]);
	return A(e, o, r, i, null);
}
function A(e, t, n, r, i) {
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
	return i == null && D.vnode != null && D.vnode(a), a;
}
function j(e) {
	return e.children;
}
function M(e, t) {
	this.props = e, this.context = t;
}
function ye(e, t) {
	if (t == null) return e.__ ? ye(e.__, e.__i + 1) : null;
	for (var n; t < e.__k.length; t++) if ((n = e.__k[t]) != null && n.__e != null) return n.__e;
	return typeof e.type == "function" ? ye(e) : null;
}
function be(e) {
	if (e.__P && e.__d) {
		var t = e.__v, n = t.__e, r = [], i = [], a = ge({}, t);
		a.__v = t.__v + 1, D.vnode && D.vnode(a), Me(e.__P, a, t, e.__n, e.__P.namespaceURI, 32 & t.__u ? [n] : null, r, n ?? ye(t), !!(32 & t.__u), i), a.__v = t.__v, a.__.__k[a.__i] = a, Pe(r, a, i), t.__e = t.__ = null, a.__e != n && xe(a);
	}
}
function xe(e) {
	if ((e = e.__) != null && e.__c != null) return e.__e = e.__c.base = null, e.__k.some(function(t) {
		if (t != null && t.__e != null) return e.__e = e.__c.base = t.__e;
	}), xe(e);
}
function Se(e) {
	(!e.__d && (e.__d = !0) && O.push(e) && !Ce.__r++ || ne != D.debounceRendering) && ((ne = D.debounceRendering) || re)(Ce);
}
function Ce() {
	try {
		for (var e, t = 1; O.length;) O.length > t && O.sort(ie), e = O.shift(), t = O.length, be(e);
	} finally {
		O.length = Ce.__r = 0;
	}
}
function we(e, t, n, r, i, a, o, s, c, l, u) {
	var d, f, p, m, h, g, _ = r && r.__k || pe, v = t.length;
	for (c = Te(n, t, _, c, v), d = 0; d < v; d++) (p = n.__k[d]) != null && (f = p.__i != -1 && _[p.__i] || fe, p.__i = d, g = Me(e, p, f, i, a, o, s, c, l, u), m = p.__e, p.ref && f.ref != p.ref && (f.ref && Le(f.ref, null, p), u.push(p.ref, p.__c || m, p)), h == null && m != null && (h = m), 4 & p.__u ? (c = Ee(p, c, e), f.__e && (f.__e = null)) : typeof p.type == "function" && g !== void 0 ? c = g : m && (c = m.nextSibling), p.__u &= -7);
	return n.__e = h, c;
}
function Te(e, t, n, r, i) {
	var a, o, s, c, l, u = n.length, d = u, f = 0;
	for (e.__k = Array(i), a = 0; a < i; a++) (o = t[a]) != null && typeof o != "boolean" && typeof o != "function" ? (typeof o == "string" || typeof o == "number" || typeof o == "bigint" || o.constructor == String ? o = e.__k[a] = A(null, o, null, null, null) : he(o) ? o = e.__k[a] = A(j, { children: o }, null, null, null) : o.constructor === void 0 && o.__b > 0 ? o = e.__k[a] = A(o.type, o.props, o.key, o.ref ? o.ref : null, o.__v) : e.__k[a] = o, c = a + f, o.__ = e, o.__b = e.__b + 1, s = null, (l = o.__i = Oe(o, n, c, d)) != -1 && (d--, (s = n[l]) && (s.__u |= 2)), s == null || s.__v == null ? (l == -1 && (i > u ? f-- : i < u && f++), typeof o.type != "function" && (o.__u |= 4)) : l != c && (l == c - 1 ? f-- : l == c + 1 ? f++ : (l > c ? f-- : f++, o.__u |= 4))) : e.__k[a] = null;
	if (d) for (a = 0; a < u; a++) (s = n[a]) != null && !(2 & s.__u) && (s.__e == r && (r = ye(s)), Re(s, s));
	return r;
}
function Ee(e, t, n) {
	var r, i;
	if (typeof e.type == "function") {
		for (r = e.__k, i = 0; r && i < r.length; i++) r[i] && (r[i].__ = e, t = Ee(r[i], t, n));
		return t;
	}
	e.__e != t && (t && e.type && !t.parentNode && (t = ye(e)), t = n.insertBefore(e.__e, t || null));
	do
		t &&= t.nextSibling;
	while (t != null && t.nodeType == 8);
	return t;
}
function De(e, t) {
	return t ||= [], e == null || typeof e == "boolean" || (he(e) ? e.some(function(e) {
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
	t[0] == "-" ? e.setProperty(t, n ?? "") : e[t] = n == null ? "" : typeof n != "number" || me.test(t) ? n : n + "px";
}
function Ae(e, t, n, r, i) {
	var a, o;
	n: if (t == "style") {
		if (typeof n == "string") e.style.cssText = n;
		else {
			if (typeof r == "string" && (e.style.cssText = r = ""), r) for (t in r) n && t in n || ke(e.style, t, "");
			if (n) for (t in n) r && n[t] == r[t] || ke(e.style, t, n[t]);
		}
	} else if (t[0] == "o" && t[1] == "n") a = t != (t = t.replace(ce, "$1")), o = t.toLowerCase(), t = o in e || t == "onFocusOut" || t == "onFocusIn" ? o.slice(2) : t.slice(2), e.l ||= {}, e.l[t + a] = n, n ? r ? n[se] = r[se] : (n[se] = le, e.addEventListener(t, a ? ue : k, a)) : e.removeEventListener(t, a ? ue : k, a);
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
			if (t[oe] == null) t[oe] = le++;
			else if (t[oe] < n[se]) return;
			return n(D.event ? D.event(t) : t);
		}
	};
}
function Me(e, t, n, r, i, a, o, s, c, l) {
	var u, d, f, p, m, h, g, _, v, y, b, x, S, C, w, T, E = t.type;
	if (t.constructor !== void 0) return null;
	128 & n.__u && (c = !!(32 & n.__u), a = [s = t.__e = n.__e]), (u = D.__b) && u(t);
	n: if (typeof E == "function") {
		d = o.length;
		try {
			if (v = t.props, y = E.prototype && E.prototype.render, b = (u = E.contextType) && r[u.__c], x = u ? b ? b.props.value : u.__ : r, n.__c ? _ = (f = t.__c = n.__c).__ = f.__E : (y ? t.__c = f = new E(v, x) : (t.__c = f = new M(v, x), f.constructor = E, f.render = ze), b && b.sub(f), f.state || (f.state = {}), f.__n = r, p = f.__d = !0, f.__h = [], f._sb = []), y && f.__s == null && (f.__s = f.state), y && E.getDerivedStateFromProps != null && (f.__s == f.state && (f.__s = ge({}, f.__s)), ge(f.__s, E.getDerivedStateFromProps(v, f.__s))), m = f.props, h = f.state, f.__v = t, p) y && E.getDerivedStateFromProps == null && f.componentWillMount != null && f.componentWillMount(), y && f.componentDidMount != null && f.__h.push(f.componentDidMount);
			else {
				if (y && E.getDerivedStateFromProps == null && v !== m && f.componentWillReceiveProps != null && f.componentWillReceiveProps(v, x), t.__v == n.__v || !f.__e && f.shouldComponentUpdate != null && !1 === f.shouldComponentUpdate(v, f.__s, x)) {
					t.__v != n.__v && (f.props = v, f.state = f.__s, f.__d = !1), t.__e = n.__e, t.__k = n.__k, t.__k.some(function(e) {
						e && (e.__ = t);
					}), pe.push.apply(f.__h, f._sb), f._sb = [], f.__h.length && o.push(f), s = ye(n);
					break n;
				}
				f.componentWillUpdate != null && f.componentWillUpdate(v, f.__s, x), y && f.componentDidUpdate != null && f.__h.push(function() {
					f.componentDidUpdate(m, h, g);
				});
			}
			if (f.context = x, f.props = v, f.__P = e, f.__e = !1, S = D.__r, C = 0, y) f.state = f.__s, f.__d = !1, S && S(t), u = f.render(f.props, f.state, f.context), pe.push.apply(f.__h, f._sb), f._sb = [];
			else do
				f.__d = !1, S && S(t), u = f.render(f.props, f.state, f.context), f.state = f.__s;
			while (f.__d && ++C < 25);
			f.state = f.__s, f.getChildContext != null && (r = ge(ge({}, r), f.getChildContext())), y && !p && f.getSnapshotBeforeUpdate != null && (g = f.getSnapshotBeforeUpdate(m, h)), w = u != null && u.type === j && u.key == null ? Fe(u.props.children) : u, s = we(e, he(w) ? w : [w], t, n, r, i, a, o, s, c, l), f.base = t.__e, t.__u &= -161, f.__h.length && o.push(f), _ && (f.__E = f.__ = null);
		} catch (e) {
			if (o.length = d, t.__v = null, c || a != null) {
				if (e.then) {
					for (t.__u |= c ? 160 : 128; s && s.nodeType == 8 && s.nextSibling;) s = s.nextSibling;
					a != null && (a[a.indexOf(s)] = null), t.__e = s;
				} else if (a != null) for (T = a.length; T--;) _e(a[T]);
			} else t.__e = n.__e;
			t.__k ??= n.__k || [], e.then || Ne(t), D.__e(e, t, n);
		}
	} else a == null && t.__v == n.__v ? (t.__k = n.__k, t.__e = n.__e) : s = t.__e = Ie(n.__e, t, n, r, i, a, o, c, l);
	return (u = D.diffed) && u(t), 128 & t.__u ? void 0 : s;
}
function Ne(e) {
	e && (e.__c && (e.__c.__e = !0), e.__k && e.__k.some(Ne));
}
function Pe(e, t, n) {
	for (var r = 0; r < n.length; r++) Le(n[r], n[++r], n[++r]);
	D.__c && D.__c(t, e), e.some(function(t) {
		try {
			e = t.__h, t.__h = [], e.some(function(e) {
				e.call(t);
			});
		} catch (e) {
			D.__e(e, t.__v);
		}
	});
}
function Fe(e) {
	return typeof e != "object" || !e || e.__b > 0 ? e : he(e) ? e.map(Fe) : e.constructor === void 0 ? ge({}, e) : null;
}
function Ie(e, t, n, r, i, a, o, s, c) {
	var l, u, d, f, p, m, h, g = n.props || fe, _ = t.props, v = t.type;
	if (v == "svg" ? i = "http://www.w3.org/2000/svg" : v == "math" ? i = "http://www.w3.org/1998/Math/MathML" : i ||= "http://www.w3.org/1999/xhtml", a != null) {
		for (l = 0; l < a.length; l++) if ((p = a[l]) && "setAttribute" in p == !!v && (v ? p.localName == v : p.nodeType == 3)) {
			e = p, a[l] = null;
			break;
		}
	}
	if (e == null) {
		if (v == null) return document.createTextNode(_);
		e = document.createElementNS(i, v, _.is && _), s &&= (D.__m && D.__m(t, a), !1), a = null;
	}
	if (v == null) g === _ || s && e.data == _ || (e.data = _);
	else {
		if (a = v == "textarea" && _.defaultValue != null ? null : a && ee.call(e.childNodes), !s && a != null) for (g = {}, l = 0; l < e.attributes.length; l++) g[(p = e.attributes[l]).name] = p.value;
		for (l in g) p = g[l], l == "dangerouslySetInnerHTML" ? d = p : l == "children" || l in _ || l == "value" && "defaultValue" in _ || l == "checked" && "defaultChecked" in _ || Ae(e, l, null, p, i);
		for (l in _) p = _[l], l == "children" ? f = p : l == "dangerouslySetInnerHTML" ? u = p : l == "value" ? m = p : l == "checked" ? h = p : s && typeof p != "function" || g[l] === p || Ae(e, l, p, g[l], i);
		if (u) s || d && (u.__html == d.__html || u.__html == e.innerHTML) || (e.innerHTML = u.__html), t.__k = [];
		else if (d && (e.innerHTML = ""), we(t.type == "template" ? e.content : e, he(f) ? f : [f], t, n, r, v == "foreignObject" ? "http://www.w3.org/1999/xhtml" : i, a, o, a ? a[0] : n.__k && ye(n, 0), s, c), a != null) for (l = a.length; l--;) _e(a[l]);
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
		D.__e(e, n);
	}
}
function Re(e, t, n) {
	var r, i;
	if (D.unmount && D.unmount(e), (r = e.ref) && (r.current && r.current != e.__e || Le(r, null, t)), (r = e.__c) != null) {
		if (r.componentWillUnmount) try {
			r.componentWillUnmount();
		} catch (e) {
			D.__e(e, t);
		}
		r.base = r.__P = r.__n = null;
	}
	if (r = e.__k) for (i = 0; i < r.length; i++) r[i] && Re(r[i], t, n || typeof e.type != "function");
	n || _e(e.__e), e.__c = e.__ = e.__e = void 0;
}
function ze(e, t, n) {
	return this.constructor(e, n);
}
function Be(e, t, n) {
	var r, i, a, o;
	t == document && (t = document.documentElement), D.__ && D.__(e, t), i = (r = typeof n == "function") ? null : n && n.__k || t.__k, a = [], o = [], Me(t, e = (!r && n || t).__k = ve(j, null, [e]), i || fe, fe, t.namespaceURI, !r && n ? [n] : i ? null : t.firstChild ? ee.call(t.childNodes) : null, a, !r && n ? n : i ? i.__e : t.firstChild, r, o), Pe(a, e, o), e.props.children = null;
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
	return t.__c = "__cC" + de++, t.__ = e, t.Provider = t.__l = (t.Consumer = function(e, t) {
		return e.children(t);
	}).contextType = t, t;
}
ee = pe.slice, D = { __e: function(e, t, n, r) {
	for (var i, a, o; t = t.__;) if ((i = t.__c) && !i.__) try {
		if ((a = i.constructor) && a.getDerivedStateFromError != null && (i.setState(a.getDerivedStateFromError(e)), o = i.__d), i.componentDidCatch != null && (i.componentDidCatch(e, r || {}), o = i.__d), o) return i.__E = i;
	} catch (t) {
		e = t;
	}
	throw e;
} }, te = 0, M.prototype.setState = function(e, t) {
	var n = this.__s != null && this.__s != this.state ? this.__s : this.__s = ge({}, this.state);
	typeof e == "function" && (e = e(ge({}, n), this.props)), e && ge(n, e), e != null && this.__v && (t && this._sb.push(t), Se(this));
}, M.prototype.forceUpdate = function(e) {
	this.__v && (this.__e = !0, e && this.__h.push(e), Se(this));
}, M.prototype.render = j, O = [], re = typeof Promise == "function" ? Promise.prototype.then.bind(Promise.resolve()) : setTimeout, ie = function(e, t) {
	return e.__v.__b - t.__v.__b;
}, Ce.__r = 0, ae = Math.random().toString(8), oe = "__d" + ae, se = "__a" + ae, ce = /(PointerCapture)$|Capture$/i, le = 0, k = je(!1), ue = je(!0), de = 0;
//#endregion
//#region node_modules/.pnpm/preact@10.29.8/node_modules/preact/hooks/dist/hooks.module.js
var He, N, Ue, We, Ge = 0, Ke = [], P = D, qe = P.__b, Je = P.__r, Ye = P.diffed, Xe = P.__c, Ze = P.unmount, Qe = P.__;
function $e(e, t) {
	P.__h && P.__h(N, e, Ge || t), Ge = 0;
	var n = N.__H || (N.__H = {
		__: [],
		__h: []
	});
	return e >= n.__.length && n.__.push({}), n.__[e];
}
function F(e) {
	return Ge = 1, et(ut, e);
}
function et(e, t, n) {
	var r = $e(He++, 2);
	if (r.t = e, !r.__c && (r.__ = [n ? n(t) : ut(void 0, t), function(e) {
		var t = r.__N ? r.__N[0] : r.__[0], n = r.t(t, e);
		t !== n && (r.__N = [n, r.__[1]], r.__c.setState({}));
	}], r.__c = N, !N.__f)) {
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
		N.__f = !0;
		var a = N.shouldComponentUpdate, o = N.componentWillUpdate;
		N.componentWillUpdate = function(e, t, n) {
			if (this.__e) {
				var r = a;
				a = void 0, i(e, t, n), a = r;
			}
			o && o.call(this, e, t, n);
		}, N.shouldComponentUpdate = i;
	}
	return r.__N || r.__;
}
function I(e, t) {
	var n = $e(He++, 3);
	!P.__s && lt(n.__H, t) && (n.__ = e, n.u = t, N.__H.__h.push(n));
}
function tt(e, t) {
	var n = $e(He++, 4);
	!P.__s && lt(n.__H, t) && (n.__ = e, n.u = t, N.__h.push(n));
}
function L(e) {
	return Ge = 5, nt(function() {
		return { current: e };
	}, []);
}
function nt(e, t) {
	var n = $e(He++, 7);
	return lt(n.__H, t) && (n.__ = e(), n.__H = t, n.__h = e), n.__;
}
function R(e, t) {
	return Ge = 8, nt(function() {
		return e;
	}, t);
}
function rt(e) {
	var t = N.context[e.__c], n = $e(He++, 9);
	return n.c = e, t ? (n.__ ?? (n.__ = !0, t.sub(N)), t.props.value) : e.__;
}
function z() {
	var e = $e(He++, 11);
	if (!e.__) {
		for (var t = N.__v; t !== null && !t.__m && t.__ !== null;) t = t.__;
		var n = t.__m || (t.__m = [0, 0]);
		e.__ = "P" + n[0] + "-" + n[1]++;
	}
	return e.__;
}
function it() {
	for (var e; e = Ke.shift();) {
		var t = e.__H;
		if (e.__P && t) try {
			t.__h.some(st), t.__h.some(ct), t.__h = [];
		} catch (n) {
			t.__h = [], P.__e(n, e.__v);
		}
	}
}
P.__b = function(e) {
	N = null, qe && qe(e);
}, P.__ = function(e, t) {
	e && t.__k && t.__k.__m && (e.__m = t.__k.__m), Qe && Qe(e, t);
}, P.__r = function(e) {
	Je && Je(e), He = 0;
	var t = (N = e.__c).__H;
	t && (Ue === N ? (t.__h = [], N.__h = [], t.__.some(function(e) {
		e.__N && (e.__ = e.__N), e.u = e.__N = void 0;
	})) : (t.__h.some(st), t.__h.some(ct), t.__h = [], He = 0)), Ue = N;
}, P.diffed = function(e) {
	Ye && Ye(e);
	var t = e.__c;
	t && t.__H && (t.__H.__h.length && (Ke.push(t) !== 1 && We === P.requestAnimationFrame || ((We = P.requestAnimationFrame) || ot)(it)), t.__H.__.some(function(e) {
		e.u &&= (e.__H = e.u, void 0);
	})), Ue = N = null;
}, P.__c = function(e, t) {
	t.some(function(e) {
		try {
			e.__h.some(st), e.__h = e.__h.filter(function(e) {
				return !e.__ || ct(e);
			});
		} catch (n) {
			t.some(function(e) {
				e.__h &&= [];
			}), t = [], P.__e(n, e.__v);
		}
	}), Xe && Xe(e, t);
}, P.unmount = function(e) {
	Ze && Ze(e);
	var t, n = e.__c;
	n && n.__H && (n.__H.__.some(function(e) {
		try {
			st(e);
		} catch (e) {
			t = e;
		}
	}), n.__H = void 0, t && P.__e(t, n.__v));
};
var at = typeof requestAnimationFrame == "function";
function ot(e) {
	var t, n = function() {
		clearTimeout(r), at && cancelAnimationFrame(t), setTimeout(e);
	}, r = setTimeout(n, 35);
	at && (t = requestAnimationFrame(n));
}
function st(e) {
	var t = N, n = e.__c;
	typeof n == "function" && (e.__c = void 0, n()), N = t;
}
function ct(e) {
	var t = N;
	e.__c = e.__(), N = t;
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
	return tt(function() {
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
		return this.shouldComponentUpdate = n, ve(e, t);
	}
	return r.displayName = "Memo(" + (e.displayName || e.name) + ")", r.__f = r.prototype.isReactComponent = !0, r.type = e, r;
}
(ht.prototype = new M()).isPureReactComponent = !0, ht.prototype.shouldComponentUpdate = function(e, t) {
	return ft(this.props, e) || ft(this.state, t);
};
var _t = D.__b;
D.__b = function(e) {
	e.type && e.type.__f && e.ref && (e.props.ref = e.ref, e.ref = null), _t && _t(e);
}, typeof Symbol < "u" && Symbol.for;
var vt = D.__e;
D.__e = function(e, t, n, r) {
	if (e.then) {
		for (var i, a = t; a = a.__;) if ((i = a.__c) && i.__c) return t.__e ?? (t.__e = n.__e, t.__k = n.__k || []), i.__c(e, t);
	}
	vt(e, t, n, r);
};
var yt = D.unmount;
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
D.unmount = function(e) {
	var t = e.__c;
	t && (t.__z = !0), t && t.__R && t.__R(), t && 32 & e.__u && (e.type = null), yt && yt(e);
}, (St.prototype = new M()).__c = function(e, t) {
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
	var i = t.__a && ve(j, null, e.fallback);
	return i && (i.__u &= -33), [ve(j, null, t.__a ? null : e.children), i];
};
var Tt = function(e, t, n) {
	if (++n[1] === n[0] && e.l.delete(t), e.props.revealOrder && (e.props.revealOrder[0] !== "t" || !e.l.size)) for (n = e.i; n;) {
		for (; n.length > 3;) n.pop()();
		if (n[1] < n[0]) break;
		e.i = n = n[2];
	}
};
(wt.prototype = new M()).__a = function(e) {
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
M.prototype.isReactComponent = !0, [
	"componentWillMount",
	"componentWillReceiveProps",
	"componentWillUpdate"
].forEach(function(e) {
	Object.defineProperty(M.prototype, e, {
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
var Nt = D.event;
D.event = function(e) {
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
}, Ft = D.vnode;
D.vnode = function(e) {
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
var It = D.__r;
D.__r = function(e) {
	It && It(e), e.__c;
};
var Lt = D.diffed;
D.diffed = function(e) {
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
//#region src/core/composer.ts
var Bt = 8388608, Vt = Object.freeze({
	text: "",
	images: Object.freeze([]),
	revision: 0,
	locked: !1,
	recoverable: Object.freeze([])
});
function Ht(e, t) {
	return t ? e ? `${e}\n\n${t}` : t : e;
}
function Ut(e, t, n) {
	if (!n.some((e) => e.name === t)) throw B("Unknown Agent command");
	let r = /^\/([^\s]+)(\s|$)/.exec(e);
	return `/${t} ${r && n.some((e) => e.name === r[1]) ? e.slice(r[0].length) : e}`;
}
function Wt(e) {
	return e.reduce((e, t) => e + t.data.length, 0);
}
function Gt(e, t) {
	if (e.length > 1048576) throw B("Draft text exceeds 1 MiB");
	if (t.length > 4 || Wt(t) > 8388608) throw B("A message allows four images and 8 MiB of base64 data");
	let n = /* @__PURE__ */ new Set();
	for (let e of t) {
		if (!e.id || n.has(e.id) || e.type !== "image" || !/^image\/(png|jpeg|webp|gif)$/.test(e.mimeType) || !e.data || e.data.length > 8388608 || e.data.length % 4 || !/^[A-Za-z0-9+/]*={0,2}$/.test(e.data)) throw B("Invalid draft image");
		n.add(e.id);
	}
}
var Kt = class {
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = new WeakSet([Vt.images]);
	#r(e) {
		if (this.#n.has(e)) return e;
		let t = Object.freeze(e.map((e) => Object.freeze({ ...e })));
		return Gt("", t), this.#n.add(t), t;
	}
	get(e) {
		return this.#e.get(e) ?? Vt;
	}
	set(e, t, n = this.get(e).images) {
		let r = this.get(e);
		if (r.locked) throw B("Wait for local submission preparation");
		this.#i(e, {
			...r,
			text: t,
			images: n,
			revision: r.revision + 1
		});
	}
	#i(e, t) {
		if (t.text.length > 1048576) throw B("Draft text exceeds 1 MiB");
		t = {
			...t,
			images: this.#r(t.images)
		};
		let n = Wt(t.images) + t.recoverable.reduce((e, t) => e + Wt(t.images), 0);
		for (let [t, r] of this.#e) t !== e && (n += Wt(r.images) + r.recoverable.reduce((e, t) => e + Wt(t.images), 0));
		for (let e of this.#t.values()) n += Wt(e.images);
		if (n > 33554432) throw B("Pending and recoverable images exceed 32 MiB");
		this.#e.set(e, Object.freeze(t));
	}
	lock(e) {
		let t = this.get(e);
		if (this.#t.has(e)) throw B("A submission is already in flight");
		if (t.locked) throw B("A draft is already being prepared");
		return this.#i(e, {
			...t,
			locked: !0
		}), {
			id: `${e}:${t.revision}`,
			text: t.text,
			images: t.images
		};
	}
	unlock(e) {
		this.#e.set(e, {
			...this.get(e),
			locked: !1
		});
	}
	dispatched(e) {
		let t = this.get(e);
		if (!t.locked || this.#t.has(e)) throw B("No prepared submission is available");
		this.#t.set(e, {
			id: `${e}:${t.revision}`,
			text: t.text,
			images: t.images
		}), this.#e.set(e, {
			...t,
			text: "",
			images: Vt.images,
			locked: !1,
			revision: t.revision + 1
		});
	}
	failed(e, t) {
		let n = this.#t.get(e);
		if (n && n.id !== t.id) throw B("Stale submission failure");
		this.#t.delete(e);
		let r = this.get(e);
		if (r.locked) {
			this.unlock(e);
			return;
		}
		!r.text && !r.images.length ? this.#i(e, {
			...r,
			text: t.text,
			images: t.images,
			revision: r.revision + 1
		}) : this.#i(e, {
			...r,
			recoverable: [...r.recoverable, t]
		});
	}
	recover(e, t) {
		let n = this.get(e);
		if (n.locked) throw B("Wait for local submission preparation");
		let r = n.recoverable.find((e) => e.id === t);
		if (!r) throw B("Failed submission is unavailable");
		this.#i(e, {
			...n,
			text: Ht(n.text, r.text),
			images: [...n.images, ...r.images],
			recoverable: n.recoverable.filter((e) => e !== r),
			revision: n.revision + 1
		});
	}
	settled(e) {
		this.#t.delete(e);
	}
	delete(e) {
		this.#e.delete(e), this.#t.delete(e);
	}
	clear() {
		this.#e.clear(), this.#t.clear();
	}
};
function B(e) {
	return new u("INVALID_CONFIGURATION", e, { phase: "composer" });
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/line-buffer.js
var qt = 10, Jt = class {
	#e = [];
	push(e) {
		let t = [], n = 0, r = e.indexOf(qt, n);
		for (; r !== -1;) t.push(this.#t(e.subarray(n, r))), n = r + 1, r = e.indexOf(qt, n);
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
async function Yt(e) {
	let { sink: t, host: n } = e, r = _({ name: e.clientInfo.name });
	r = r.onRequest(T.client.session.requestPermission, async ({ params: e }) => {
		let n = e, r = await t.onPermission(e.sessionId, en(n), n);
		return g(r);
	}).onRequest(T.client.elicitation.create, async ({ params: e }) => {
		let n = e, r = await t.onElicitation("sessionId" in e && typeof e.sessionId == "string" ? e.sessionId : void 0, y(n), n);
		return w(r);
	}).onNotification(T.client.session.update, ({ params: e }) => {
		t.onProtocol(T.client.session.update, e), t.onUpdate(e.sessionId, e.update);
	}).onNotification(T.client.elicitation.complete, ({ params: e }) => {
		t.onProtocol(T.client.elicitation.complete, e), t.onElicitationComplete(e.elicitationId);
	});
	let i = n?.v1?.filesystem;
	i?.readTextFile && (r = r.onRequest(T.client.fs.readTextFile, async ({ params: e }) => await i.readTextFile(e))), i?.writeTextFile && (r = r.onRequest(T.client.fs.writeTextFile, async ({ params: e }) => await i.writeTextFile(e)));
	let a = n?.v1?.terminal;
	a && (r = r.onRequest(T.client.terminal.create, async ({ params: e }) => await a.create(e)).onRequest(T.client.terminal.output, async ({ params: e }) => await a.output(e)).onRequest(T.client.terminal.release, async ({ params: e }) => await a.release(e)).onRequest(T.client.terminal.waitForExit, async ({ params: e }) => await a.waitForExit(e)).onRequest(T.client.terminal.kill, async ({ params: e }) => await a.kill(e)));
	let s = r.connect(e.stream), c = !1;
	s.closed.then(() => {
		c && t.onDisconnect();
	});
	let l;
	try {
		if (l = await s.agent.request(T.agent.initialize, {
			protocolVersion: 1,
			clientInfo: {
				name: e.clientInfo.name,
				version: e.clientInfo.version,
				...e.clientInfo.title ? { title: e.clientInfo.title } : {}
			},
			clientCapabilities: {
				fs: {
					readTextFile: !!i?.readTextFile,
					writeTextFile: !!i?.writeTextFile
				},
				terminal: !!a,
				session: { configOptions: { boolean: {} } },
				auth: { terminal: !!n?.terminalAuth },
				elicitation: {
					form: {},
					url: {}
				}
			}
		}), s.signal.aborted) throw s.signal.reason;
	} catch (e) {
		throw s.close(e), new u("INITIALIZE_REJECTED", "ACP v1 initialization failed", {
			cause: e,
			protocol: 1,
			phase: "initialize",
			retryable: !0
		});
	}
	if (l.protocolVersion !== 1) throw s.close(), new u("PROTOCOL_VERSION_MISMATCH", `Requested ACP v1 but agent selected v${l.protocolVersion}`, {
		protocol: 1,
		phase: "initialize"
	});
	let d = l.agentCapabilities, f = d?.sessionCapabilities, p = new Xt(s, {
		protocolVersion: 1,
		...l.agentInfo?.title || l.agentInfo?.name ? { agentName: l.agentInfo.title ?? l.agentInfo.name } : {},
		authMethods: o(l.authMethods),
		capabilities: {
			listSessions: f?.list != null,
			loadSession: d?.loadSession === !0,
			resumeSession: f?.resume != null,
			closeSession: f?.close != null,
			deleteSession: f?.delete != null
		},
		promptCapabilities: {
			image: d?.promptCapabilities?.image === !0,
			audio: d?.promptCapabilities?.audio === !0,
			embeddedContext: d?.promptCapabilities?.embeddedContext === !0
		},
		additionalDirectories: f?.additionalDirectories != null,
		mcp: {
			stdio: !0,
			http: d?.mcpCapabilities?.http === !0,
			sse: d?.mcpCapabilities?.sse === !0
		}
	}, t, n, () => {
		c = !1;
	});
	return c = !0, p;
}
var Xt = class {
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
		p(e, this.initialized, 1, "session/new");
		let t = await b(() => this.connection.agent.request(T.agent.session.new, Zt(e)), 1, "session/new");
		return this.#e.set(t.sessionId, !t.configOptions?.length && !!t.modes), $t(t.sessionId, t.configOptions, t.modes);
	}
	async openSession(e, t, n) {
		p(t, this.initialized, 1, "session/open");
		let r = {
			...Zt(t),
			sessionId: e
		};
		if (n === "all" && this.initialized.capabilities.loadSession) {
			let t = await b(() => this.connection.agent.request(T.agent.session.load, r), 1, "session/open");
			return this.#e.set(e, !t.configOptions?.length && !!t.modes), $t(e, t.configOptions, t.modes);
		}
		if (!this.initialized.capabilities.resumeSession) throw new u("CAPABILITY_REQUIRED", "The agent cannot open existing sessions", {
			protocol: 1,
			phase: "session/resume"
		});
		let i = await b(() => this.connection.agent.request(T.agent.session.resume, r), 1, "session/open");
		return this.#e.set(e, !i.configOptions?.length && !!i.modes), $t(e, i.configOptions, i.modes, n === "all");
	}
	async listSessions(e, t) {
		if (!this.initialized.capabilities.listSessions) throw new u("CAPABILITY_REQUIRED", "The agent does not support session/list", { protocol: 1 });
		let n = await this.connection.agent.request(T.agent.session.list, {
			cwd: e,
			...t ? { cursor: t } : {}
		});
		return a(n);
	}
	async deleteSession(e) {
		if (!this.initialized.capabilities.deleteSession) throw new u("CAPABILITY_REQUIRED", "The agent does not support session/delete", { protocol: 1 });
		await this.connection.agent.request(T.agent.session.delete, { sessionId: e }), this.#e.delete(e);
	}
	async closeSession(e) {
		if (!this.initialized.capabilities.closeSession) {
			this.#e.delete(e);
			return;
		}
		await this.connection.agent.request(T.agent.session.close, { sessionId: e }), this.#e.delete(e);
	}
	promptReady(e) {
		return !0;
	}
	async prompt(e, t, n) {
		let r = !1;
		try {
			let i = this.connection.agent.request(T.agent.session.prompt, {
				sessionId: e,
				prompt: t
			});
			return r = !0, n(), (await i).stopReason;
		} catch (e) {
			throw f(e, 1, r);
		}
	}
	async cancel(e) {
		await this.connection.agent.notify(T.agent.session.cancel, { sessionId: e });
	}
	async setConfigOption(e, t, n) {
		if (this.#e.get(e) && t === "mode" && typeof n == "string") return await this.connection.agent.request(T.agent.session.setMode, {
			sessionId: e,
			modeId: n
		}), [];
		let r = await this.connection.agent.request(T.agent.session.setConfigOption, {
			sessionId: e,
			configId: t,
			value: n,
			...typeof n == "boolean" ? { type: "boolean" } : {}
		});
		return c(r.configOptions);
	}
	async authenticate(e) {
		if (e.type === "terminal") {
			if (!this.host?.terminalAuth) throw new u("CAPABILITY_REQUIRED", "Terminal authentication needs a host handler", { protocol: 1 });
			await this.host.terminalAuth(e);
			return;
		}
		await this.connection.agent.request(T.agent.authenticate, { methodId: e.id });
	}
	async logout() {
		await this.connection.agent.request(T.agent.logout, {}), this.#e.clear();
	}
	async close(e) {
		this.markClosed(), this.#e.clear(), this.connection.close(e), await this.connection.closed;
	}
};
function Zt(e) {
	return {
		cwd: e.cwd,
		mcpServers: (e.mcpServers ?? []).map(Qt),
		...e.additionalDirectories?.length ? { additionalDirectories: [...e.additionalDirectories] } : {}
	};
}
function Qt(e) {
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
function $t(e, n, r, i = !1) {
	let a = c(n);
	return {
		sessionId: e,
		configOptions: a.length ? a : t(r),
		...i ? { historyGap: i } : {}
	};
}
function en(t) {
	let r = n(t) ? t : {}, i = n(r.toolCall) ? r.toolCall : {};
	return {
		type: "permission",
		title: e(i.title) ?? "Permission required",
		options: S(r.options)
	};
}
//#endregion
//#region src/core/protocol/connect.ts
async function tn(e) {
	if (e.protocol === 1) return nn(1, 1, e);
	if (e.protocol === 2) return nn(2, 1, e);
	let t = await e.connector.open({
		protocol: 2,
		attempt: 1,
		signal: e.signal
	}), n = an(t);
	try {
		return await rn(n.stream, e);
	} catch (r) {
		if (n.negotiatedVersion() !== 1) throw r;
		return await cn(t), nn(1, 2, e);
	}
}
async function nn(e, t, n) {
	let r = await n.connector.open({
		protocol: e,
		attempt: t,
		signal: n.signal
	});
	if (n.signal.aborted) throw await cn(r), new u("CONNECTION_CLOSED", "Connection was cancelled", {
		protocol: e,
		retryable: !0
	});
	return e === 1 ? Yt({
		stream: r,
		sink: n.sink,
		clientInfo: n.clientInfo,
		...n.host ? { host: n.host } : {}
	}) : rn(r, n);
}
async function rn(e, t) {
	let { connectV2: n } = await import("./chunks/v2.js");
	return n({
		stream: e,
		sink: t.sink,
		clientInfo: t.clientInfo,
		...t.host ? { host: t.host } : {}
	});
}
function an(e) {
	let t, n, r = e.writable, i = e.readable, a = new WritableStream({
		async write(e) {
			let n = on(e);
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
				for (let e of i) !sn(e) || e.id !== t || !sn(e.result) || typeof e.result.protocolVersion == "number" && (n = e.result.protocolVersion);
				r.enqueue(e);
			} })),
			writable: a
		},
		negotiatedVersion: () => n
	};
}
function on(e) {
	let t = Array.isArray(e) ? e : [e];
	for (let e of t) if (sn(e) && e.method === "initialize" && Object.hasOwn(e, "id")) return { id: e.id };
}
function sn(e) {
	return typeof e == "object" && !!e && !Array.isArray(e);
}
async function cn(e) {
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
var ln = 2097152;
function un(e, t = ln) {
	let n;
	try {
		n = JSON.stringify(e);
	} catch {
		return !1;
	}
	return n !== void 0 && dn(n, t);
}
function dn(e, t) {
	let n = 0;
	for (let r = 0; r < e.length; r += 1) {
		let i = e.charCodeAt(r);
		if (i <= 127 ? n += 1 : i <= 2047 ? n += 2 : i >= 55296 && i <= 56319 && r + 1 < e.length && e.charCodeAt(r + 1) >= 56320 && e.charCodeAt(r + 1) <= 57343 ? (n += 4, r += 1) : n += 3, n > t) return !1;
	}
	return !0;
}
function fn(e) {
	if (e === void 0) return ln;
	if (!Number.isSafeInteger(e) || e <= 0) throw RangeError("maxMessageBytes must be a positive safe integer");
	return e;
}
//#endregion
//#region src/core/chat-controller.ts
var pn = {
	listSessions: !1,
	loadSession: !1,
	resumeSession: !1,
	closeSession: !1,
	deleteSession: !1
}, mn = 16384, hn = 16384, gn = 1024;
function _n(e) {
	return new vn(e);
}
var vn = class {
	#e = new Kt();
	#t = /* @__PURE__ */ new Set();
	#n;
	#r = /* @__PURE__ */ new Map();
	#i = 0;
	#a = /* @__PURE__ */ new Map();
	ready;
	#o;
	#s = /* @__PURE__ */ new Set();
	#c;
	#l;
	#u;
	#d = /* @__PURE__ */ new Map();
	#f = /* @__PURE__ */ new Map();
	#p;
	#m = /* @__PURE__ */ new Map();
	#h = /* @__PURE__ */ new Map();
	#g = [];
	#_;
	#v;
	#y = 0;
	#b = 0;
	#x = 0;
	#S = 0;
	#C = !1;
	#w;
	#T = 0;
	#E = "connecting";
	#D;
	#O = [];
	#k;
	#A;
	#j;
	#M = /* @__PURE__ */ new Map();
	#N;
	#P;
	#F = !1;
	constructor(e) {
		this.#o = e, this.#n = fn(e.connector.maxMessageBytes), this.#k = this.#fe(), this.#A = this.#pe(), this.#u = bn(e.context), this.#v = {
			draft: Vt,
			promptCapabilities: {
				image: !1,
				audio: !1,
				embeddedContext: !1
			},
			phase: "connecting",
			loadedSessions: [],
			historyGap: !1,
			activities: [],
			configOptions: [],
			commands: [],
			contextSelection: this.#_e(),
			interactions: [],
			authMethods: [],
			capabilities: pn,
			sessionTrail: []
		}, yn(e.context) && (this.#c = e.context.subscribe(() => {
			this.#C || this.#ge();
		})), this.ready = this.#L(!0), this.ready.catch(() => void 0);
	}
	getSnapshot() {
		return this.#v;
	}
	subscribe(e) {
		return this.#s.add(e), () => this.#s.delete(e);
	}
	setDraft(e) {
		this.#e.set(this.#oe().instanceId, e), this.#ye();
	}
	appendDraft(e) {
		let t = this.#oe().instanceId;
		this.setDraft(Ht(this.#e.get(t).text, e));
	}
	addDraftImages(e) {
		let t = this.#oe().instanceId;
		C(e, this.#re().initialized.promptCapabilities, this.#re().version);
		let n = this.#e.get(t);
		this.#e.set(t, n.text, [...n.images, ...e]), this.#ye();
	}
	removeDraftImage(e) {
		let t = this.#oe().instanceId, n = this.#e.get(t);
		this.#e.set(t, n.text, n.images.filter((t) => t.id !== e)), this.#ye();
	}
	selectCommand(e) {
		let t = this.#oe();
		this.setDraft(Ut(this.#e.get(t.instanceId).text, e, t.commands));
	}
	sendDraft() {
		let e = this.#oe(), t = e.instanceId, n = this.#e.lock(t);
		try {
			let r = [...n.text.trim() ? [{
				type: "text",
				text: n.text
			}] : [], ...n.images.map(({ data: e, mimeType: t }) => ({
				type: "image",
				data: e,
				mimeType: t
			}))], i = this.send(r);
			return e.activeTurn.draft = {
				key: t,
				submission: n
			}, this.#ye(), i;
		} catch (e) {
			throw this.#e.unlock(t), this.#ye(), e;
		}
	}
	recoverDraft(e) {
		this.#e.recover(this.#oe().instanceId, e), this.#ye();
	}
	getComposerActions() {
		return this.#o.composerActions?.() ?? [];
	}
	async runComposerAction(e) {
		if (e.disabled || !e.run) return !1;
		let t = this.#oe(), n = this.#S, r = new AbortController();
		this.#t.add(r);
		try {
			let i = await e.run({
				sessionInstanceId: t.instanceId,
				signal: r.signal
			});
			return this.#C || r.signal.aborted || this.#ae() !== t || this.#S !== n || typeof i != "string" ? !1 : (this.appendDraft(i), !0);
		} finally {
			this.#t.delete(r);
		}
	}
	#I(e, t) {
		if (!un({
			jsonrpc: "2.0",
			id: 2 ** 53 - 1,
			method: "session/prompt",
			params: {
				sessionId: e,
				prompt: t
			}
		}, this.#n)) throw new u("INVALID_CONFIGURATION", `The prepared ACP prompt exceeds the ${this.#n} byte wire-message limit`, {
			phase: "prompt",
			protocol: this.#_?.version
		});
	}
	appendNotice(e) {
		if (this.#C) return !1;
		if (!n(e) || typeof e.text != "string" || e.text.length === 0 || !dn(e.text, hn) || e.level !== "info" && e.level !== "error" || e.sessionId !== void 0 && (typeof e.sessionId != "string" || e.sessionId.trim().length === 0)) throw new u("INVALID_CONFIGURATION", `Notice text must contain 1 to ${hn} UTF-8 bytes, use an info or error level, and target a non-empty session ID when provided`, { phase: "notice" });
		let t = e.sessionId ?? this.#v.sessionId;
		if (!t) return !1;
		let r = this.#d.get(t);
		return r ? (r.timeline.addNotice({
			type: "notice",
			id: `host-notice-${++this.#y}`,
			text: e.text,
			level: e.level
		}), this.#ue(r), !0) : !1;
	}
	send(e) {
		this.#Q();
		let t = this.#oe();
		if (this.#M.has(t.sessionId)) throw new u("SESSION_BUSY", `Wait for the current operation on session '${t.sessionId}'`, {
			protocol: this.#_?.version,
			phase: "prompt"
		});
		if (t.activeTurn) throw new u("SESSION_BUSY", "Wait for the current turn to finish", {
			protocol: this.#_?.version,
			phase: "prompt"
		});
		if (t.phase !== "idle" || !this.#re().promptReady(t.sessionId)) throw new u("SESSION_BUSY", `Session '${t.sessionId}' is not ready for another prompt`, {
			protocol: this.#_?.version,
			phase: "prompt"
		});
		let n = Sn(e);
		if (n.some((e) => e._meta !== null && e._meta !== void 0 && Object.hasOwn(e._meta, "pretty-aui/context"))) throw new u("INVALID_CONFIGURATION", "Prompt input cannot use the reserved pretty-aui/context metadata key", { phase: "prompt" });
		if (!n.length || n.every((e) => e.type === "text" && typeof e.text == "string" && !e.text.trim())) throw new u("INVALID_CONFIGURATION", "A prompt cannot be empty", { phase: "prompt" });
		C(n, this.#re().initialized.promptCapabilities, this.#re().version), this.#o.context || this.#I(t.sessionId, n);
		let r = `turn-${++this.#y}`, i = new AbortController(), a = {
			id: r,
			sessionId: t.sessionId,
			abort: i,
			contextSelection: this.#u,
			cancelled: !1,
			submitted: !1
		};
		t.activeTurn = a, t.timeline.beginTurn(), t.timeline.addUserMessage(n, !0, Date.now()), t.phase = "running", t.stopReason = void 0, t.error = void 0, this.#ue(t, !0), this.#xe({
			type: "turn_started",
			sessionId: t.sessionId,
			turnId: r
		});
		let o = this.#z(a, n);
		return o.catch(() => void 0), {
			id: r,
			done: o
		};
	}
	async addContext() {
		let e = this.#me("add");
		if (!e.add) throw new u("METHOD_NOT_AVAILABLE", "The context provider does not support adding context", { phase: "context/add" });
		await this.#he("context/add", () => e.add());
	}
	async removeContext(e) {
		let t = this.#me("remove");
		if (!t.remove) throw new u("METHOD_NOT_AVAILABLE", "The context provider does not support removing context", { phase: "context/remove" });
		if (!this.#u.some((t) => t.id === e)) throw new u("INVALID_CONFIGURATION", `Unknown context selection '${e}'`, { phase: "context/remove" });
		await this.#he("context/remove", () => t.remove(e));
	}
	async cancel(e) {
		let t = this.#oe(e), n = t.activeTurn;
		if (!n || n.cancelled || (n.cancelled = !0, n.abort.abort(Nn), this.#X(t.sessionId), t.phase = "cancelling", this.#ue(t, !0), !n.submitted)) return;
		let r = this.#_;
		if (r) try {
			await r.cancel(t.sessionId);
		} catch (e) {
			throw t.activeTurn === n && (n.cancelled = !1, this.#ie(e, t.sessionId)), e;
		}
	}
	async reconnect() {
		this.#ee(), await this.#Te("connection/reconnect", () => this.#L(!1));
	}
	async newSession() {
		this.#te();
		try {
			await this.#Te("session/new", async () => {
				let e = this.#re(), t = await this.#H(e), n = this.#se(t);
				this.#ce(n);
			});
		} catch (e) {
			throw this.#ne(e, "session/new");
		}
	}
	async listSessions(e) {
		let t = this.#N;
		if (t) {
			if (t.cursor === e) return t.operation;
			throw new u("SESSION_BUSY", "Wait for the current session-list request to finish", {
				protocol: this.#_?.version,
				phase: "session/list"
			});
		}
		let n = this.#re(), r = Symbol("session/list"), i = Promise.resolve().then(async () => {
			try {
				let t = await n.listSessions(this.#o.session.cwd, e);
				this.#De(n);
				let r = e && this.#v.sessions ? {
					sessions: Mn([...this.#v.sessions.sessions, ...t.sessions]).slice(0, 1e3),
					...t.nextCursor ? { nextCursor: t.nextCursor } : {}
				} : t;
				return this.#Ce(r.sessions), this.#v = xn({
					...this.#v,
					sessions: r
				}), this.#ye(), r;
			} finally {
				this.#N?.token === r && (this.#N = void 0);
			}
		});
		return this.#N = {
			cursor: e,
			operation: i,
			token: r
		}, i;
	}
	async openSession(e) {
		let t = ++this.#S, n = this.#d.get(e);
		if (n) {
			t === this.#S && this.#ce(n);
			return;
		}
		this.#te(), await this.#Ee(e, "session/open", async () => this.#V(this.#re(), e, [], t));
	}
	async openChildSession(e) {
		let t = this.#oe();
		if (this.#$(t, "session/open-child"), e === t.sessionId) return;
		let n = [...this.#v.sessionTrail, {
			sessionId: t.sessionId,
			...t.sessionTitle ? { title: t.sessionTitle } : {}
		}], r = ++this.#S, i = this.#d.get(e);
		if (i) {
			this.#ce(i, n);
			return;
		}
		this.#te(), await this.#Ee(e, "session/open-child", async () => this.#V(this.#re(), e, n, r));
	}
	async openAncestorSession(e) {
		this.#$(this.#oe(), "session/open-ancestor");
		let t = this.#v.sessionTrail.findIndex((t) => t.sessionId === e);
		if (t < 0) throw new u("INVALID_CONFIGURATION", `Session '${e}' is not an ancestor of the active session`, { phase: "session/open-ancestor" });
		let n = this.#v.sessionTrail.slice(0, t), r = ++this.#S, i = this.#d.get(e);
		if (i) {
			this.#ce(i, n);
			return;
		}
		this.#te(), await this.#Ee(e, "session/open-ancestor", async () => this.#V(this.#re(), e, n, r));
	}
	async closeSession(e) {
		let t = this.#oe(e);
		this.#$(t, "session/close"), await this.#Ee(t.sessionId, "session/close", async () => {
			let e = this.#re();
			if (await e.closeSession(t.sessionId), this.#De(e), this.#X(t.sessionId), this.#e.delete(t.instanceId), this.#d.delete(t.sessionId), this.#v.sessionId === t.sessionId) {
				let e = [...this.#d.values()].sort((e, t) => t.lastSelected - e.lastSelected)[0];
				e ? this.#ce(e) : this.#le();
			} else this.#ye();
		});
	}
	async deleteSession(e) {
		if (e === this.#v.sessionId) throw new u("INVALID_CONFIGURATION", "The active session cannot be deleted", { phase: "session/delete" });
		let t = this.#d.get(e);
		t && this.#$(t, "session/delete"), await this.#Ee(e, "session/delete", async () => {
			let n = this.#re();
			if (await n.deleteSession(e), this.#De(n), t) {
				this.#X(e);
				let t = this.#d.get(e);
				t && this.#e.delete(t.instanceId), this.#d.delete(e);
			}
			this.#v.sessions && (this.#v = xn({
				...this.#v,
				sessions: {
					...this.#v.sessions,
					sessions: this.#v.sessions.sessions.filter((t) => t.sessionId !== e)
				}
			})), this.#ye();
		});
	}
	async setConfigOption(e, t) {
		let n = this.#oe();
		this.#$(n, "session/set-config"), await this.#Ee(n.sessionId, "session/set-config", async () => {
			let r = this.#re(), i = await r.setConfigOption(n.sessionId, e, t);
			this.#De(r), n.configOptions = i.length ? i : n.configOptions.map((n) => n.id === e ? {
				...n,
				currentValue: t
			} : n), this.#de(n), this.#ue(n);
		});
	}
	async authenticate(e) {
		if (this.#o.allowAuthentication === !1) throw new u("AUTHENTICATION_DISABLED", "Agent authentication is disabled by the host", { phase: "auth/login" });
		let t = this.#v.authMethods.find((t) => t.id === e);
		if (!t) throw new u("INVALID_CONFIGURATION", `Unknown authentication method '${e}'`);
		await this.#Te("auth/login", async () => {
			let e = this.#re();
			this.#E = "connecting", this.#D = void 0, this.#ye();
			try {
				await e.authenticate(t), this.#De(e);
				let n = await this.#H(e);
				this.#E = "ready";
				let r = this.#se(n);
				this.#ce(r);
			} catch (e) {
				throw this.#ie(e), e;
			}
		});
	}
	async logout() {
		this.#ee(), await this.#Te("auth/logout", async () => {
			let e = this.#re();
			await e.logout(), this.#De(e), this.#X(), this.#d.clear(), this.#e.clear(), this.#E = "auth_required", this.#le();
		});
	}
	respondPermission(e, t) {
		let n = this.#m.get(e);
		return n ? (this.#m.delete(e), n.resolve(t), this.#Y(e, n.sessionId), !0) : !1;
	}
	respondElicitation(e, t) {
		let n = this.#h.get(e);
		return n ? (this.#h.delete(e), n.resolve(t), this.#Y(e, n.sessionId), !0) : !1;
	}
	async destroy() {
		if (this.#C) return;
		this.#C = !0;
		for (let e of this.#t) e.abort();
		this.#t.clear(), this.#e.clear(), this.#r.clear(), this.#a.clear(), this.#c?.(), this.#c = void 0, this.#l = void 0, this.#T += 1, this.#p?.abort();
		let e = new u("TURN_INTERRUPTED", "Chat was destroyed before the turn completed", {
			phase: "destroy",
			retryable: !1
		});
		for (let t of this.#d.values()) t.activeTurn?.abort.abort(e);
		this.#X();
		for (let e of this.#d.values()) e.timeline.reset();
		let t = this.#_;
		this.#_ = void 0, this.#f.clear(), this.#E = "closed", this.#ye(), await t?.close().catch(() => void 0), this.#s.clear();
	}
	onUpdate(e, t) {
		if (this.#C) return;
		let n = this.#f.get(e), r = this.#d.get(e);
		if (!n && !r) {
			this.#xe({
				type: "diagnostic",
				sessionId: e,
				code: "UNKNOWN_SESSION_UPDATE",
				message: `Ignored an update for unloaded session '${e}'`
			});
			return;
		}
		let i = (n?.timeline ?? r.timeline).reduce(t, this.#_?.version ?? 1);
		if (n) {
			this.#K(n, i);
			return;
		}
		let a = this.#W(r, i);
		this.#ue(r, a);
	}
	onPermission(e, t, n) {
		let r = this.#d.get(e);
		if (this.#C || !r?.activeTurn || !this.#G()) return Promise.resolve({ outcome: "cancelled" });
		let i = `permission-${++this.#y}`, a = {
			...t,
			id: i
		};
		return new Promise((t) => {
			this.#m.set(i, {
				sessionId: e,
				interaction: a,
				resolve: t
			}), this.#J(a, e);
		});
	}
	onElicitation(e, t, n) {
		if (this.#C || e !== void 0 && !this.#d.has(e) || t.elicitationId !== void 0 && this.#Z(t.elicitationId) !== void 0 || !this.#G()) return Promise.resolve({ action: "cancel" });
		let r = `elicitation-${++this.#y}`, i = {
			...t,
			id: r
		};
		return new Promise((t) => {
			this.#h.set(r, {
				...e === void 0 ? {} : { sessionId: e },
				interaction: i,
				resolve: t
			}), this.#J(i, e);
		});
	}
	onElicitationComplete(e) {
		if (this.#C) return;
		let t = this.#Z(e);
		if (!t) return;
		let n = this.#h.get(t);
		n && (this.#h.delete(t), n.resolve({ action: "accept" }), this.#Y(t, n.sessionId));
	}
	onProtocol(e, t) {
		let n = this.#_?.version;
		n && this.#xe({
			type: "protocol",
			protocolVersion: n,
			method: e,
			raw: t
		});
	}
	onDisconnect() {
		if (!this.#C) {
			if (!this.#_ && this.#w) {
				let e = this.#T;
				this.#w.then(() => {
					this.#Oe(e) && this.onDisconnect();
				}, () => void 0);
				return;
			}
			this.#X(), this.#ie(new u("CONNECTION_CLOSED", "The ACP connection closed", {
				protocol: this.#_?.version,
				phase: "connection",
				retryable: !0
			}));
		}
	}
	async #L(e) {
		if (this.#w) return this.#w;
		let t = this.#R(e);
		return this.#w = t, t.then(() => {
			this.#w === t && (this.#w = void 0);
		}, () => {
			this.#w === t && (this.#w = void 0);
		}), t;
	}
	async #R(e) {
		if (this.#C) throw V();
		let t = ++this.#T;
		this.#p?.abort();
		let n = new AbortController();
		this.#p = n, this.#E = "connecting", this.#D = void 0, this.#ye();
		let r = this.#_, i = this.#v.sessionId, a = this.#O, o = [...this.#d.values()];
		r && (this.#_ = void 0, await r.close().catch(() => void 0), this.#ke(t));
		let s;
		try {
			if (s = await tn({
				connector: this.#o.connector,
				protocol: this.#o.protocol ?? 1,
				signal: n.signal,
				sink: this,
				clientInfo: {
					name: this.#o.clientInfo?.name ?? "pretty-aui",
					version: this.#o.clientInfo?.version ?? "0.1.0",
					...this.#o.clientInfo?.title ? { title: this.#o.clientInfo.title } : {}
				},
				...this.#o.host ? { host: this.#o.host } : {}
			}), !this.#Oe(t)) throw await s.close().catch(() => void 0), V();
			if (this.#_ = s, this.#v = xn({
				...this.#v,
				protocolVersion: s.version,
				agentName: s.initialized.agentName,
				authMethods: this.#o.allowAuthentication === !1 ? [] : s.initialized.authMethods,
				capabilities: s.initialized.capabilities
			}), this.#ye(), this.#xe({
				type: "connected",
				protocolVersion: s.version
			}), e) {
				let e = this.#o.initialSession ?? { type: "new" };
				if (e.type === "none") {
					this.#d.clear(), this.#e.clear(), this.#E = "ready", this.#le();
					return;
				}
				if (e.type === "open") {
					this.#te(), await this.#V(s, e.sessionId, [], ++this.#S), this.#E = "ready", this.#ye();
					return;
				}
				let n = await this.#H(s);
				this.#ke(t, s), this.#d.clear(), this.#e.clear(), this.#E = "ready", this.#ce(this.#se(n));
				return;
			}
			if (!o.length) {
				this.#E = "ready", this.#le();
				return;
			}
			if (!s.initialized.capabilities.resumeSession && !s.initialized.capabilities.loadSession) {
				let e = await this.#H(s);
				this.#ke(t, s), this.#d.clear(), this.#e.clear(), this.#E = "ready", this.#ce(this.#se(e));
				return;
			}
			let r = [...o].sort((e, t) => e.sessionId === i ? -1 : t.sessionId === i ? 1 : t.lastSelected - e.lastSelected);
			for (let e of r) try {
				let n = s.initialized.capabilities.resumeSession ? "none" : "all", r = n === "none" ? e.timeline : new E(), o = {
					sessionId: e.sessionId,
					timeline: r,
					configOptions: e.configOptions,
					commands: e.commands,
					sessionTitle: e.sessionTitle,
					sessionTitleSource: e.sessionTitleSource
				};
				this.#f.set(e.sessionId, o);
				let c = await s.openSession(e.sessionId, this.#o.session, n);
				this.#ke(t, s), n === "all" && this.#K(o, r.finalizeReplay());
				let l = this.#se(c, r, o, e.instanceId);
				l.lastSelected = e.lastSelected, l.usage = e.usage, e.sessionId === i && this.#ce(l, a);
			} catch (t) {
				if (e.sessionId === i) throw t;
				e.phase = "error", e.error = l(t), this.#d.set(e.sessionId, e);
			} finally {
				this.#f.delete(e.sessionId);
			}
			this.#E = "ready", this.#ye();
		} catch (e) {
			if (!this.#Oe(t)) throw s && this.#_ === s && (this.#_ = void 0), await s?.close().catch(() => void 0), V();
			if (e instanceof u && e.code === "AUTHENTICATION_REQUIRED" && s?.initialized.authMethods.length) {
				if (this.#o.allowAuthentication === !1) {
					let t = new u("AUTHENTICATION_DISABLED", "The agent requires authentication disabled by the host", {
						cause: e,
						protocol: s?.version,
						phase: "session/new"
					});
					throw this.#ie(t), t;
				}
				throw this.#E = "auth_required", this.#D = void 0, this.#ye(), new u("AUTHENTICATION_REQUIRED", "Authentication is required before a session can be created", {
					cause: e,
					protocol: s?.version,
					phase: "session/new"
				});
			}
			throw this.#ie(e), e;
		}
	}
	async #z(e, t) {
		try {
			let n = this.#re(), r = this.#oe(e.sessionId), a = await this.#B(r.sessionId, t, e.contextSelection, e.abort.signal);
			Pn(e.abort.signal);
			let o = a.map((e) => ({
				...e,
				content: e.content.map((t) => Cn(t, e))
			})), s = o.length ? i(t, x()) : t, c = [...o.flatMap((e) => e.content), ...s];
			C(c, n.initialized.promptCapabilities, n.version), this.#I(r.sessionId, c), Pn(e.abort.signal), e.submitted = !0;
			let l = await n.prompt(r.sessionId, c, () => {
				this.#C || (e.dispatched = !0, e.draft && this.#e.dispatched(e.draft.key), r.timeline.markUserAccepted(o), this.#ue(r));
			});
			return this.#Se(e, e.cancelled ? "cancelled" : l);
		} catch (t) {
			if (e.draft && !this.#C && ((!e.dispatched || t instanceof u && t.accepted === !1) && this.#e.failed(e.draft.key, e.draft.submission), this.#e.settled(e.draft.key)), e.cancelled || t === Nn) return this.#Se(e, "cancelled");
			let n = this.#d.get(e.sessionId);
			throw n?.activeTurn === e && (n.activeTurn = void 0, n.timeline.finishTurn()), this.#ie(t, e.sessionId), t;
		}
	}
	async #B(e, t, r, i) {
		try {
			let a = this.#o.context;
			if (!a) return [];
			let o = yn(a) ? await Fn(a.resolve({
				sessionId: e,
				input: t,
				selection: r,
				...this.#v.protocolVersion ? { protocolVersion: this.#v.protocolVersion } : {},
				capabilities: this.#re().initialized.promptCapabilities,
				signal: i
			}), i) : a;
			if (yn(a) && (o.length !== r.length || o.some((e, t) => e.id !== r[t]?.id))) throw Error("Resolved context IDs must match the frozen selection order");
			let s = /* @__PURE__ */ new Set();
			if (o.length > 64) throw Error("Context is limited to 64 items per turn");
			for (let e of o) {
				if (!n(e) || typeof e.id != "string" || !e.id.trim() || e.id.length > 16384) throw Error("Context item IDs must be non-empty bounded strings");
				if (s.has(e.id)) throw Error(`Context item IDs must be unique: '${e.id}'`);
				if (typeof e.label != "string" || !e.label.trim() || e.label.length > 16384) throw Error("Context item labels must be non-empty bounded strings");
				if (!Array.isArray(e.content) || !e.content.length) throw Error("Context items must contain at least one content block");
				s.add(e.id);
			}
			let c = o.map((e) => ({
				id: e.id,
				label: e.label,
				content: e.content.map(wn)
			})), l = this.#re();
			return C(c.flatMap((e) => e.content), l.initialized.promptCapabilities, l.version), c;
		} catch (e) {
			throw i.aborted ? i.reason ?? e : new u("CONTEXT_FAILED", Dn(e), {
				cause: e,
				protocol: this.#_?.version,
				phase: "context",
				retryable: !0
			});
		}
	}
	async #V(e, t, n, r) {
		let i = {
			sessionId: t,
			timeline: new E(),
			configOptions: [],
			commands: [],
			sessionTitle: void 0,
			sessionTitleSource: void 0
		};
		this.#f.set(t, i);
		try {
			let a = await e.openSession(t, this.#o.session, "all");
			this.#De(e), this.#K(i, i.timeline.finalizeReplay());
			let o = this.#se(a, i.timeline, i);
			r === this.#S ? this.#ce(o, n) : this.#ye();
		} finally {
			this.#f.get(t) === i && this.#f.delete(t);
		}
	}
	async #H(e) {
		let t = await e.newSession(this.#o.session);
		this.#De(e), t = await this.#U(e, t);
		let n = En(t.configOptions), r = this.#k;
		if (!n || !r || n.currentValue === r || !n.options?.some((e) => e.value === r)) return t;
		try {
			let i = await e.setConfigOption(t.sessionId, n.id, r);
			return this.#De(e), kn(t, n, r, i);
		} catch {
			if (this.#De(e), this.#E === "error") throw V();
			return this.#xe({
				type: "diagnostic",
				sessionId: t.sessionId,
				code: "MODEL_PREFERENCE_APPLY_FAILED",
				message: "The preferred model could not be applied; using the Agent default"
			}), t;
		}
	}
	async #U(e, t) {
		let n = On(t.configOptions), r = this.#A;
		if (!n || !r || n.currentValue === r || !n.options?.some((e) => e.value === r)) return t;
		try {
			let i = await e.setConfigOption(t.sessionId, n.id, r);
			return this.#De(e), kn(t, n, r, i);
		} catch {
			if (this.#De(e), this.#E === "error") throw V();
			return this.#xe({
				type: "diagnostic",
				sessionId: t.sessionId,
				code: "NEW_SESSION_MODE_APPLY_FAILED",
				message: "The fixed new-session mode could not be applied; using the Agent default"
			}), t;
		}
	}
	#W(e, t) {
		let n = !1;
		return t.state && !e.activeTurn && (e.phase !== "cancelling" || t.state !== "idle") ? this.#xe({
			type: "diagnostic",
			sessionId: e.sessionId,
			code: "STALE_SESSION_STATE",
			message: `Ignored ${t.state} state without an active turn`
		}) : (t.state === "running" && (e.phase = "running", n = !0), t.state === "requires_action" && (e.phase = "awaiting_user", n = !0), t.state === "idle" && (e.phase = "idle", t.stopReason && (e.stopReason = t.stopReason), n = !0)), t.commands && (e.commands = t.commands), t.configOptions && (e.configOptions = t.configOptions), t.sessionTitle !== void 0 && (e.sessionTitle = t.sessionTitle ?? void 0, e.sessionTitleSource = "notification", n = !0), t.usage && (e.usage = t.usage), t.unsupported && this.#xe({
			type: "diagnostic",
			sessionId: e.sessionId,
			code: "UNSUPPORTED_UPDATE",
			message: t.unsupported
		}), this.#q(e.sessionId, t), n;
	}
	#G() {
		return this.#m.size + this.#h.size < 16 || (this.#xe({
			type: "diagnostic",
			code: "INTERACTION_LIMIT",
			message: "Cancelled an interaction beyond the 16-interaction limit"
		}), !1);
	}
	#K(e, t) {
		t.commands && (e.commands = t.commands), t.configOptions && (e.configOptions = t.configOptions), t.sessionTitle !== void 0 && (e.sessionTitle = t.sessionTitle ?? void 0, e.sessionTitleSource = "notification"), this.#q(e.sessionId, t);
	}
	#q(e, t) {
		for (let n of t.diagnostics ?? []) this.#xe({
			type: "diagnostic",
			sessionId: e,
			code: n.code,
			message: n.message
		});
	}
	#J(e, t) {
		if (t === void 0) {
			this.#g = [...this.#g, e], this.#ye();
			return;
		}
		let n = this.#d.get(t);
		n && (n.interactions = [...n.interactions, e], n.phase = "awaiting_user", this.#ue(n, !0));
	}
	#Y(e, t) {
		if (t === void 0) {
			this.#g = this.#g.filter((t) => t.id !== e), this.#ye();
			return;
		}
		let n = this.#d.get(t);
		n && (n.interactions = n.interactions.filter((t) => t.id !== e), n.phase = n.interactions.length ? "awaiting_user" : n.activeTurn ? "running" : "idle", this.#ue(n, !0));
	}
	#X(e) {
		for (let [t, n] of this.#m) (e === void 0 || n.sessionId === e) && (this.#m.delete(t), n.resolve({ outcome: "cancelled" }));
		for (let [t, n] of this.#h) (e === void 0 || n.sessionId === e) && (this.#h.delete(t), n.resolve({ action: "cancel" }));
		if (e === void 0) {
			this.#g = [];
			for (let e of this.#d.values()) e.interactions = [], e.activeTurn || (e.phase = "idle");
			this.#ye();
			return;
		}
		let t = this.#d.get(e);
		t && (t.interactions = [], t.phase = t.activeTurn ? "running" : "idle", this.#ue(t, !0));
	}
	#Z(e) {
		for (let [t, n] of this.#h) if (n.interaction.type === "elicitation" && n.interaction.elicitationId === e) return t;
	}
	#Q() {
		if (this.#C) throw new u("CONNECTION_CLOSED", "Chat has been destroyed");
		if (this.#E !== "ready" || !this.#_ || !this.#v.sessionId) throw new u("SESSION_NOT_READY", "The chat session is not ready", { phase: "prompt" });
		if (this.#v.phase === "auth_required") throw new u("SESSION_NOT_READY", "Authenticate before sending a prompt", { phase: "prompt" });
	}
	#$(e, t) {
		if (e.activeTurn || e.interactions.length) throw new u("SESSION_BUSY", `Finish session '${e.sessionId}' before changing it`, { phase: t });
	}
	#ee() {
		if (this.#C) throw V();
		if (this.#g.length || [...this.#d.values()].some((e) => e.activeTurn || e.interactions.length)) throw new u("SESSION_BUSY", "Finish all turns and interactions before replacing the connection", { phase: "connection/reconnect" });
	}
	#te() {
		let e = [...this.#f.keys()].filter((e) => !this.#d.has(e)).length;
		if (!(this.#d.size + e < 16)) throw new u("SESSION_LIMIT", "Close a loaded session before opening another one", { phase: "session" });
	}
	#ne(e, t) {
		if (!(e instanceof u) || e.code !== "AUTHENTICATION_REQUIRED" || !this.#_?.initialized.authMethods.length) return e;
		if (this.#o.allowAuthentication === !1) {
			let n = new u("AUTHENTICATION_DISABLED", "The agent requires authentication disabled by the host", {
				cause: e,
				protocol: this.#_.version,
				phase: t
			});
			return this.#ie(n), n;
		}
		return this.#E = "auth_required", this.#D = void 0, this.#ye(), new u("AUTHENTICATION_REQUIRED", "Authentication is required before a session can be created", {
			cause: e,
			protocol: this.#_.version,
			phase: t
		});
	}
	#re() {
		if (this.#C) throw V();
		if (!this.#_) throw new u("SESSION_NOT_READY", "The ACP connection is not ready");
		return this.#_;
	}
	#ie(e, t) {
		if (this.#C) return;
		let n = l(e), r = t ? this.#d.get(t) : void 0;
		if (r) {
			r.phase = "error", r.error = n, this.#ue(r, !0), this.#xe({
				type: "error",
				sessionId: r.sessionId,
				error: n
			});
			return;
		}
		this.#E = "error", this.#D = n, this.#ye(), this.#xe({
			type: "error",
			error: n
		});
	}
	#ae() {
		let e = this.#v.sessionId;
		return e ? this.#d.get(e) : void 0;
	}
	#oe(e = this.#v.sessionId) {
		if (!e) throw new u("SESSION_NOT_READY", "No active session", { phase: "session" });
		let t = this.#d.get(e);
		if (!t) throw new u("SESSION_NOT_READY", `Session '${e}' is not loaded`, { phase: "session" });
		return t;
	}
	#se(e, t = new E(), n, r = `session-instance-${++this.#x}`) {
		let i = this.#v.sessions?.sessions.find((t) => t.sessionId === e.sessionId)?.title, a = n?.sessionTitleSource === "notification", o = a ? n?.sessionTitle : n?.sessionTitle ?? i, s = {
			sessionId: e.sessionId,
			instanceId: r,
			timeline: t,
			phase: "idle",
			activeTurn: void 0,
			configOptions: e.configOptions.length ? e.configOptions : n?.configOptions ?? [],
			commands: n?.commands ?? e.commands ?? [],
			interactions: [],
			sessionTitle: o,
			sessionTitleSource: a ? "notification" : o === void 0 ? void 0 : "catalog",
			historyGap: e.historyGap ?? !1,
			usage: void 0,
			stopReason: void 0,
			error: void 0,
			lastSelected: 0
		};
		return this.#d.set(e.sessionId, s), s;
	}
	#ce(e, t = []) {
		for (let e of this.#t) e.abort();
		e.lastSelected = ++this.#b, this.#de(e), this.#O = [...t], this.#v = xn({
			...this.#v,
			sessionId: e.sessionId
		}), this.#ye(), this.#xe({
			type: "session_changed",
			sessionId: e.sessionId
		}), e.sessionTitle === void 0 && e.sessionTitleSource !== "notification" && this.#we();
	}
	#le() {
		this.#O = [], this.#v = xn({
			...this.#v,
			sessionId: void 0
		}), this.#ye(), this.#xe({ type: "session_changed" });
	}
	#ue(e, t = !1) {
		this.#v.sessionId === e.sessionId ? (this.#de(e), this.#ye()) : t && this.#ye();
	}
	#de(e) {
		let t = En(e.configOptions);
		if (!(!t || typeof t.currentValue != "string" || !An(t.currentValue) || this.#k === t.currentValue)) {
			this.#k = t.currentValue;
			try {
				this.#o.modelPreference?.set(t.currentValue);
			} catch {
				this.#xe({
					type: "diagnostic",
					sessionId: e.sessionId,
					code: "MODEL_PREFERENCE_WRITE_FAILED",
					message: "The host could not persist the current model preference"
				});
			}
		}
	}
	#fe() {
		let e;
		try {
			e = this.#o.modelPreference?.get();
		} catch {
			this.#xe({
				type: "diagnostic",
				code: "MODEL_PREFERENCE_READ_FAILED",
				message: "The host model preference could not be read"
			});
			return;
		}
		if (e !== void 0) {
			if (An(e)) return e;
			this.#xe({
				type: "diagnostic",
				code: "INVALID_MODEL_PREFERENCE",
				message: "Ignored an invalid host model preference"
			});
		}
	}
	#pe() {
		let e = this.#o.newSessionMode;
		if (e !== void 0) {
			if (jn(e)) return e;
			this.#xe({
				type: "diagnostic",
				code: "INVALID_NEW_SESSION_MODE",
				message: "Ignored an invalid fixed new-session mode"
			});
		}
	}
	#me(e) {
		if (this.#C) throw V();
		let t = this.#o.context;
		if (!yn(t)) throw new u("METHOD_NOT_AVAILABLE", "The configured context is not mutable", { phase: `context/${e}` });
		return t;
	}
	async #he(e, t) {
		if (this.#C) throw V();
		if (this.#l) throw new u("SESSION_BUSY", "Wait for the current context change to finish", { phase: e });
		let n = Symbol(e);
		this.#l = n, this.#ye();
		try {
			if (await t(), this.#C || this.#l !== n) throw V();
			this.#ge();
		} catch (t) {
			throw this.#C ? V() : new u("CONTEXT_FAILED", "Context selection could not be changed", {
				cause: t,
				phase: e,
				retryable: !0
			});
		} finally {
			this.#l === n && (this.#l = void 0, this.#ye());
		}
	}
	#ge() {
		this.#u = bn(this.#o.context), this.#ye();
	}
	#_e() {
		let e = this.#o.context;
		return {
			items: this.#u,
			canAdd: !!(yn(e) && e.add),
			canRemove: !!(yn(e) && e.remove),
			busy: this.#l !== void 0
		};
	}
	#ve() {
		let e = [...this.#d.values()].map((e) => e.timeline);
		if (e.length === this.#a.size && e.every((e) => this.#a.get(e) === e.imageRevision)) return;
		let t = /* @__PURE__ */ new Set(), n = [], r = 0;
		for (let e of this.#d.values()) for (let i of e.timeline.imagePayloads()) {
			let a = `${e.instanceId}:${i.activityId}`;
			t.add(a), this.#r.has(a) || this.#r.set(a, ++this.#i), !i.protected && (r += i.bytes, n.push({
				session: e,
				id: i.activityId,
				key: a,
				bytes: i.bytes,
				order: this.#r.get(a)
			}));
		}
		for (let e of this.#r.keys()) t.has(e) || this.#r.delete(e);
		n.sort((e, t) => e.order - t.order);
		for (let e of n) {
			if (r <= 67108864) break;
			e.session.timeline.evictImages(e.id), this.#r.delete(e.key), r -= e.bytes;
		}
		this.#a = new Map(e.map((e) => [e, e.imageRevision]));
	}
	#ye() {
		if (this.#C && this.#E !== "closed") return;
		this.#ve();
		let e = this.#ae(), t = this.#E, n = t === "ready" ? e?.phase ?? "idle" : t, r = t === "error" ? this.#D : e?.error;
		this.#v = xn({
			protocolVersion: this.#v.protocolVersion,
			agentName: this.#v.agentName,
			loadedSessions: [...this.#d.values()].map((e) => ({
				sessionId: e.sessionId,
				...e.sessionTitle ? { title: e.sessionTitle } : {},
				phase: e.phase,
				interactionCount: e.interactions.length,
				...e.error ? { error: e.error } : {}
			})),
			sessionId: e?.sessionId,
			sessionInstanceId: e?.instanceId,
			sessionTitle: e?.sessionTitle,
			sessionTrail: this.#O,
			historyGap: e?.historyGap ?? !1,
			activities: e?.timeline.activities ?? [],
			configOptions: e?.configOptions ?? [],
			commands: e?.commands ?? [],
			draft: e ? this.#e.get(e.instanceId) : Vt,
			promptCapabilities: this.#_?.initialized.promptCapabilities ?? {
				image: !1,
				audio: !1,
				embeddedContext: !1
			},
			contextSelection: this.#_e(),
			interactions: [...e?.interactions ?? [], ...this.#g],
			authMethods: this.#v.authMethods,
			sessions: this.#v.sessions,
			capabilities: this.#v.capabilities,
			usage: e?.usage,
			stopReason: e?.stopReason,
			error: r,
			phase: n
		}), this.#be();
	}
	#be() {
		for (let e of this.#s) try {
			e();
		} catch {}
	}
	#xe(e) {
		if (!this.#C) try {
			this.#o.onEvent?.(e);
		} catch {}
	}
	#Se(e, t) {
		if (this.#C) throw V();
		let n = this.#oe(e.sessionId);
		return e.draft && (this.#e.settled(e.draft.key), e.dispatched || this.#e.unlock(e.draft.key)), n.activeTurn === e && (n.activeTurn = void 0), n.timeline.finishTurn(t === "cancelled" ? void 0 : Date.now()), n.phase = this.#_?.promptReady(n.sessionId) ? "idle" : "cancelling", n.stopReason = t, this.#ue(n, !0), this.#xe({
			type: "turn_completed",
			sessionId: n.sessionId,
			turnId: e.id,
			stopReason: t
		}), t !== "cancelled" && n.sessionTitleSource !== "notification" && this.#we(), { stopReason: t };
	}
	#Ce(e) {
		for (let t of e) {
			if (t.title === void 0) continue;
			let e = this.#d.get(t.sessionId);
			!e || e.sessionTitleSource === "notification" || (e.sessionTitle = t.title, e.sessionTitleSource = "catalog");
		}
	}
	#we() {
		if (this.#C || !this.#v.capabilities.listSessions || !this.#_ || (this.#F = !0, this.#P)) return;
		let e = this.#_, t = Promise.resolve().then(async () => {
			for (; this.#F && !this.#C;) {
				this.#F = !1;
				let t = this.#N, n = !1;
				if (t) try {
					await t.operation, n = t.cursor === void 0;
				} catch {}
				if (this.#C || this.#_ !== e) return;
				if (!n) try {
					await this.listSessions();
				} catch {
					if (this.#C || this.#_ !== e) return;
					this.#xe({
						type: "diagnostic",
						code: "SESSION_TITLE_REFRESH_FAILED",
						message: "The session title could not be refreshed from the Agent catalog"
					});
				}
			}
		}).finally(() => {
			this.#P === t && (this.#P = void 0, this.#F && this.#we());
		});
		this.#P = t;
	}
	async #Te(e, t) {
		if (this.#C) throw V();
		if (this.#j) throw new u("SESSION_BUSY", "Wait for the current connection-level session operation to finish", {
			protocol: this.#_?.version,
			phase: e
		});
		if (this.#M.size) throw new u("SESSION_BUSY", "Wait for target-session operations to finish", {
			protocol: this.#_?.version,
			phase: e
		});
		let n = Symbol(e);
		this.#j = n;
		try {
			return await t();
		} finally {
			this.#j === n && (this.#j = void 0);
		}
	}
	async #Ee(e, t, n) {
		if (this.#C) throw V();
		if (this.#j) throw new u("SESSION_BUSY", "Wait for the current connection-level session operation to finish", {
			protocol: this.#_?.version,
			phase: t
		});
		if (this.#M.has(e)) throw new u("SESSION_BUSY", `Wait for the current operation on session '${e}'`, {
			protocol: this.#_?.version,
			phase: t
		});
		let r = Symbol(t);
		this.#M.set(e, r);
		try {
			return await n();
		} finally {
			this.#M.get(e) === r && this.#M.delete(e);
		}
	}
	#De(e) {
		if (this.#C || this.#_ !== e) throw V();
	}
	#Oe(e) {
		return !this.#C && this.#T === e;
	}
	#ke(e, t) {
		if (!this.#Oe(e) || t !== void 0 && this.#_ !== t) throw V();
	}
};
function yn(e) {
	return !Array.isArray(e) && n(e) && typeof e.getSelection == "function" && typeof e.subscribe == "function" && typeof e.resolve == "function";
}
function bn(e) {
	if (!e) return Object.freeze([]);
	let t = yn(e) ? e.getSelection() : e;
	if (!Array.isArray(t)) throw new u("INVALID_CONFIGURATION", "Context selection must be an array", { phase: "context/selection" });
	if (t.length > 64) throw new u("INVALID_CONFIGURATION", "Context is limited to 64 selected items", { phase: "context/selection" });
	let r = /* @__PURE__ */ new Set(), i = t.map((e) => {
		if (!n(e) || typeof e.id != "string" || !e.id.trim() || e.id.length > 16384) throw new u("INVALID_CONFIGURATION", "Context selection IDs must be non-empty bounded strings", { phase: "context/selection" });
		if (r.has(e.id)) throw new u("INVALID_CONFIGURATION", `Context selection IDs must be unique: '${e.id}'`, { phase: "context/selection" });
		if (typeof e.label != "string" || !e.label.trim() || e.label.length > 16384) throw new u("INVALID_CONFIGURATION", "Context selection labels must be non-empty bounded strings", { phase: "context/selection" });
		return r.add(e.id), Object.freeze({
			id: e.id,
			label: e.label
		});
	});
	return Object.freeze(i);
}
function xn(e) {
	let t = { ...e };
	for (let [e, n] of Object.entries(t)) n === void 0 && delete t[e];
	return t;
}
function Sn(e) {
	return typeof e == "string" ? [{
		type: "text",
		text: e
	}] : Array.isArray(e) ? [...e] : [e];
}
function Cn(e, t) {
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
function wn(e) {
	if (!n(e) || typeof e.type != "string" || !e.type) throw Error("Context content blocks require a type");
	if (n(e._meta) && Object.hasOwn(e._meta, "pretty-aui/context")) throw Error("Context blocks cannot use reserved pretty-aui metadata");
	let t = Tn(e);
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
					let t = s(e);
					return t ? [t] : [];
				}) } : {}
			};
		case "resource": {
			if (!n(e.resource) || typeof e.resource.uri != "string") throw Error("Context resources require a uri");
			let r = e.resource, i = r.uri, a = s(r._meta);
			return {
				...t,
				type: "resource",
				resource: {
					uri: i,
					...typeof r.mimeType == "string" || r.mimeType === null ? { mimeType: r.mimeType } : {},
					...typeof r.text == "string" ? { text: r.text } : {},
					...typeof r.blob == "string" ? { blob: r.blob } : {},
					...a ? { _meta: a } : {}
				}
			};
		}
		default: return {
			...s(e) ?? {},
			...t,
			type: e.type
		};
	}
}
function Tn(e) {
	let t = s(e._meta), r = n(e.annotations) ? {
		...Array.isArray(e.annotations.audience) ? { audience: e.annotations.audience.filter((e) => e === "user" || e === "assistant") } : {},
		...typeof e.annotations.priority == "number" && Number.isFinite(e.annotations.priority) ? { priority: e.annotations.priority } : {},
		...typeof e.annotations.lastModified == "string" ? { lastModified: e.annotations.lastModified.slice(0, 16384) } : {}
	} : void 0;
	return {
		...r ? { annotations: r } : {},
		...t ? { _meta: t } : {}
	};
}
function En(e) {
	return e.find((e) => e.category === "model" && e.type === "select") ?? e.find((e) => e.id === "model" && e.type === "select");
}
function Dn(e) {
	let t = "Context could not be prepared; the prompt was not sent";
	if (!(e instanceof Error)) return t;
	let n = e.message.trim();
	if (!n) return t;
	let r = n.slice(0, gn), i = r.charCodeAt(r.length - 1);
	return i >= 55296 && i <= 56319 && (r = r.slice(0, -1)), n.length > gn && (r += "…"), `${t}: ${r}`;
}
function On(e) {
	return e.find((e) => e.category === "mode" && e.type === "select") ?? e.find((e) => e.id === "mode" && e.type === "select");
}
function kn(e, t, n, r) {
	return {
		...e,
		configOptions: r.length ? r : e.configOptions.map((e) => e.id === t.id ? {
			...e,
			currentValue: n
		} : e)
	};
}
function An(e) {
	return jn(e);
}
function jn(e) {
	return typeof e == "string" && e.length > 0 && dn(e, mn);
}
function Mn(e) {
	let t = /* @__PURE__ */ new Set();
	return e.filter((e) => !t.has(e.sessionId) && (t.add(e.sessionId), !0));
}
var Nn = Symbol("turn-cancelled");
function Pn(e) {
	if (e.aborted) throw e.reason ?? Nn;
}
function Fn(e, t) {
	return t.aborted ? Promise.reject(t.reason ?? Nn) : new Promise((n, r) => {
		let i = () => {
			r(t.reason ?? Nn);
		};
		t.addEventListener("abort", i, { once: !0 }), Promise.resolve(e).then((e) => {
			t.removeEventListener("abort", i), n(e);
		}, (e) => {
			t.removeEventListener("abort", i), r(e);
		});
	});
}
function V() {
	return new u("CONNECTION_CLOSED", "Chat ownership ended before the operation completed", {
		phase: "connection",
		retryable: !1
	});
}
//#endregion
//#region src/react/composer-images.ts
var In = Promise.resolve(), Ln = 0, Rn = class extends Error {
	issue;
	constructor(e) {
		super(`Image validation failed: ${e}`), this.issue = e;
	}
};
function zn(e) {
	let t = In.then(async () => {
		let t = Uint8Array.from(atob(e.data), (e) => e.charCodeAt(0)), n = URL.createObjectURL(new Blob([t], { type: e.mimeType })), r = new Image();
		try {
			return r.src = n, await r.decode(), n;
		} catch (e) {
			throw URL.revokeObjectURL(n), e;
		} finally {
			r.src = "";
		}
	});
	return In = t.then(() => void 0, () => void 0), t;
}
function Bn(e, t) {
	let n = In.then(async () => {
		if (e.length + t.length > 4) throw new Rn("count");
		let n = Bt - Wt(t), r = [];
		for (let t of e) {
			let e = 4 * Math.ceil(t.size / 3);
			if (!t.size || e > n) throw new Rn("budget");
			let i = new Uint8Array(await t.arrayBuffer()), a = Vn(i);
			if (!a || t.type && t.type !== a) throw new Rn("type");
			let o = Hn(i, a);
			o && Un(...o), await Wn(new Blob([i], { type: a }));
			let s = "";
			for (let e = 0; e < i.length; e += 32768) s += String.fromCharCode(...i.subarray(e, e + 32768));
			r.push({
				type: "image",
				id: `image-${++Ln}`,
				name: t.name || "image",
				mimeType: a,
				data: btoa(s)
			}), n -= e;
		}
		return r;
	}).catch((e) => {
		throw e instanceof Rn ? e : new Rn("decode");
	});
	return In = n.then(() => void 0, () => void 0), n;
}
function Vn(e) {
	let t = (t, n) => String.fromCharCode(...e.subarray(t, n));
	if ([
		137,
		80,
		78,
		71,
		13,
		10,
		26,
		10
	].every((t, n) => e[n] === t)) return "image/png";
	if (e[0] === 255 && e[1] === 216 && e[2] === 255) return "image/jpeg";
	if (["GIF87a", "GIF89a"].includes(t(0, 6))) return "image/gif";
	if (t(0, 4) === "RIFF" && t(8, 12) === "WEBP") return "image/webp";
}
function Hn(e, t) {
	let n = new DataView(e.buffer, e.byteOffset, e.byteLength);
	if (t === "image/png" && e.length >= 24) return [n.getUint32(16), n.getUint32(20)];
	if (t === "image/gif" && e.length >= 10) return [n.getUint16(6, !0), n.getUint16(8, !0)];
	if (t === "image/jpeg") for (let t = 2; t + 9 < e.length && e[t] === 255;) {
		let r = e[t + 1];
		if (r === 255) {
			t++;
			continue;
		}
		let i = n.getUint16(t + 2);
		if (i < 2) break;
		if ([
			192,
			193,
			194,
			195,
			197,
			198,
			199,
			201,
			202,
			203,
			205,
			206,
			207
		].includes(r)) return [n.getUint16(t + 7), n.getUint16(t + 5)];
		t += i + 2;
	}
	if (t === "image/webp" && e.length >= 30) {
		let t = String.fromCharCode(...e.subarray(12, 16)), r = (t) => e[t] | e[t + 1] << 8 | e[t + 2] << 16;
		if (t === "VP8X") return [1 + r(24), 1 + r(27)];
		if (t === "VP8 ") return [n.getUint16(26, !0) & 16383, n.getUint16(28, !0) & 16383];
		if (t === "VP8L") {
			let e = n.getUint32(21, !0);
			return [1 + (e & 16383), 1 + (e >>> 14 & 16383)];
		}
	}
}
function Un(e, t) {
	if (e <= 0 || t <= 0 || e > 8e3 || t > 8e3 || e * t > 16e6) throw new Rn("dimensions");
}
async function Wn(e) {
	if (typeof createImageBitmap == "function") {
		let t = await createImageBitmap(e);
		try {
			Un(t.width, t.height);
		} finally {
			t.close();
		}
		return;
	}
	let t = URL.createObjectURL(e), n = new Image();
	try {
		n.src = t, await n.decode(), Un(n.naturalWidth, n.naturalHeight);
	} finally {
		n.src = "", URL.revokeObjectURL(t);
	}
}
//#endregion
//#region node_modules/.pnpm/preact@10.29.8/node_modules/preact/jsx-runtime/dist/jsxRuntime.module.js
var Gn = 0;
Array.isArray;
function H(e, t, n, r, i, a) {
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
		__v: --Gn,
		__i: -1,
		__u: 0,
		__source: i,
		__self: a
	};
	if (typeof e == "function" && (o = e.defaultProps)) for (s in o) c[s] === void 0 && (c[s] = o[s]);
	return D.vnode && D.vnode(l), l;
}
//#endregion
//#region src/react/ComposerImages.tsx
function Kn({ images: e, sessionInstanceId: t, disabled: n, remove: r, labels: i }) {
	let [a, o] = F(/* @__PURE__ */ new Map());
	return I(() => {
		let t = !0, n = /* @__PURE__ */ new Map();
		return o(/* @__PURE__ */ new Map()), (async () => {
			for (let r of e) {
				if (!t) break;
				try {
					let e = await zn(r);
					if (!t) {
						URL.revokeObjectURL(e);
						break;
					}
					n.set(r.id, e), o(new Map(n));
				} catch {}
			}
		})(), () => {
			t = !1;
			for (let e of n.values()) URL.revokeObjectURL(e);
		};
	}, [e, t]), /* @__PURE__ */ H(j, { children: e.map((e) => /* @__PURE__ */ H("span", {
		className: "paui-context-chip",
		children: [
			a.get(e.id) && /* @__PURE__ */ H("img", {
				src: a.get(e.id),
				alt: e.name
			}),
			/* @__PURE__ */ H("span", { children: e.name }),
			/* @__PURE__ */ H("button", {
				type: "button",
				disabled: n,
				"aria-label": i.removeImage(e.name),
				onClick: () => r(e.id),
				children: "×"
			})
		]
	}, e.id)) });
}
//#endregion
//#region src/react/ComposerMenu.tsx
function qn({ controller: e, snapshot: t, labels: n, disabled: r, onImages: i, runAction: a, focusComposer: o }) {
	let [s, c] = F([]), l = L(null), u = L(null), d = L([]), f = L(void 0), p = () => {
		c([]), l.current?.focus();
	};
	I(() => {
		c([]);
	}, [t.sessionInstanceId]), I(() => {
		if (!s.length) return;
		let e = Array.from(u.current?.querySelectorAll("button:not(:disabled)") ?? []);
		(e.find((e) => e.dataset.action === f.current) ?? e[0])?.focus(), f.current = void 0;
		let t = (e) => {
			!e.composedPath().includes(u.current) && !e.composedPath().includes(l.current) && c([]);
		};
		return document.addEventListener("pointerdown", t), () => document.removeEventListener("pointerdown", t);
	}, [s]);
	let m = () => {
		if (s.length <= 1) {
			p();
			return;
		}
		f.current = d.current.pop(), c(s.slice(0, -1));
	};
	return /* @__PURE__ */ H("div", {
		className: "paui-composer-menu",
		children: [/* @__PURE__ */ H("button", {
			ref: l,
			type: "button",
			className: "paui-context-add",
			"aria-label": n.composerAdd,
			"aria-haspopup": "menu",
			"aria-expanded": !!s.length,
			disabled: r,
			onClick: () => {
				if (s.length) {
					p();
					return;
				}
				d.current = [];
				let r = [
					{
						id: "images",
						label: n.addImages,
						disabled: !t.promptCapabilities.image,
						...t.promptCapabilities.image ? {} : { description: n.imagesUnsupported },
						run: () => {
							i();
						}
					},
					...t.commands.length ? [{
						id: "commands",
						label: n.commands,
						children: t.commands.map((t) => ({
							id: `command:${t.name}`,
							label: `/${t.name}`,
							run: () => {
								e.selectCommand(t.name), o();
							}
						}))
					}] : [],
					...e.getComposerActions(),
					...t.contextSelection.canAdd ? [{
						id: "context",
						label: n.addContext,
						disabled: t.contextSelection.busy,
						run: async () => {
							await e.addContext();
						}
					}] : []
				];
				c([r]);
			},
			children: "+"
		}), s.length > 0 && /* @__PURE__ */ H("div", {
			ref: u,
			role: "menu",
			"aria-label": n.composerAdd,
			className: "paui-composer-menu__panel",
			onKeyDown: (e) => {
				if (e.key === "Escape" || e.key === "ArrowLeft") e.preventDefault(), e.stopPropagation(), m();
				else if ([
					"ArrowDown",
					"ArrowUp",
					"Home",
					"End"
				].includes(e.key)) {
					e.preventDefault();
					let t = Array.from(u.current?.querySelectorAll("button:not(:disabled)") ?? []), n = t.indexOf(e.target);
					t[e.key === "Home" ? 0 : e.key === "End" ? t.length - 1 : (n + (e.key === "ArrowDown" ? 1 : -1) + t.length) % t.length]?.focus();
				} else if (e.key === "ArrowRight") {
					let t = e.target;
					t.getAttribute("aria-haspopup") === "menu" && (e.preventDefault(), t.click());
				} else e.key === "Tab" && c([]);
			},
			children: [s.length > 1 && /* @__PURE__ */ H("button", {
				type: "button",
				role: "menuitem",
				onClick: m,
				children: ["← ", n.back]
			}), s.at(-1).map((t) => /* @__PURE__ */ H("button", {
				type: "button",
				role: "menuitem",
				"data-action": t.id,
				disabled: t.disabled,
				title: t.description,
				"aria-description": t.description,
				"aria-haspopup": t.children ? "menu" : void 0,
				onClick: () => {
					t.children ? (d.current.push(t.id), c([...s, t.children])) : (p(), a(async () => {
						await e.runComposerAction(t) && o();
					}));
				},
				children: [t.label, t.children ? " ›" : ""]
			}, t.id))]
		})]
	});
}
//#endregion
//#region node_modules/.pnpm/dompurify@3.4.14/node_modules/dompurify/dist/purify.es.mjs
function Jn(e, t) {
	(t == null || t > e.length) && (t = e.length);
	for (var n = 0, r = Array(t); n < t; n++) r[n] = e[n];
	return r;
}
function Yn(e) {
	if (Array.isArray(e)) return e;
}
function Xn(e, t) {
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
function Zn() {
	throw TypeError("Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.");
}
function Qn(e, t) {
	return Yn(e) || Xn(e, t) || $n(e, t) || Zn();
}
function $n(e, t) {
	if (e) {
		if (typeof e == "string") return Jn(e, t);
		var n = {}.toString.call(e).slice(8, -1);
		return n === "Object" && e.constructor && (n = e.constructor.name), n === "Map" || n === "Set" ? Array.from(e) : n === "Arguments" || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n) ? Jn(e, t) : void 0;
	}
}
var er = Object.entries, tr = Object.setPrototypeOf, nr = Object.isFrozen, rr = Object.getPrototypeOf, ir = Object.getOwnPropertyDescriptor, U = Object.freeze, W = Object.seal, ar = Object.create, or = typeof Reflect < "u" && Reflect, sr = or.apply, cr = or.construct;
U ||= function(e) {
	return e;
}, W ||= function(e) {
	return e;
}, sr ||= function(e, t) {
	var n = [...arguments].slice(2);
	return e.apply(t, n);
}, cr ||= function(e) {
	return new e(...[...arguments].slice(1));
};
var lr = q(Array.prototype.forEach), ur = q(Array.prototype.lastIndexOf), dr = q(Array.prototype.pop), fr = q(Array.prototype.push), pr = q(Array.prototype.splice), mr = Array.isArray, hr = q(String.prototype.toLowerCase), gr = q(String.prototype.toString), _r = q(String.prototype.match), vr = q(String.prototype.replace), yr = q(String.prototype.indexOf), br = q(String.prototype.trim), xr = q(Number.prototype.toString), Sr = q(Boolean.prototype.toString), Cr = typeof BigInt > "u" ? null : q(BigInt.prototype.toString), wr = typeof Symbol > "u" ? null : q(Symbol.prototype.toString), G = q(Object.prototype.hasOwnProperty), Tr = q(Object.prototype.toString), K = q(RegExp.prototype.test), Er = Dr(TypeError);
function q(e) {
	return function(t) {
		t instanceof RegExp && (t.lastIndex = 0);
		var n = [...arguments].slice(1);
		return sr(e, t, n);
	};
}
function Dr(e) {
	return function() {
		return cr(e, [...arguments]);
	};
}
function J(e, t) {
	let n = arguments.length > 2 && arguments[2] !== void 0 ? arguments[2] : hr;
	if (tr && tr(e, null), !mr(t)) return e;
	let r = t.length;
	for (; r--;) {
		let i = t[r];
		if (typeof i == "string") {
			let e = n(i);
			e !== i && (nr(t) || (t[r] = e), i = e);
		}
		e[i] = !0;
	}
	return e;
}
function Or(e) {
	for (let t = 0; t < e.length; t++) G(e, t) || (e[t] = null);
	return e;
}
function Y(e) {
	let t = ar(null);
	for (let r of er(e)) {
		var n = Qn(r, 2);
		let i = n[0], a = n[1];
		G(e, i) && (t[i] = mr(a) ? Or(a) : a && typeof a == "object" && a.constructor === Object ? Y(a) : a);
	}
	return t;
}
function kr(e) {
	switch (typeof e) {
		case "string": return e;
		case "number": return xr(e);
		case "boolean": return Sr(e);
		case "bigint": return Cr ? Cr(e) : "0";
		case "symbol": return wr ? wr(e) : "Symbol()";
		case "undefined": return Tr(e);
		case "function":
		case "object": {
			if (e === null) return Tr(e);
			let t = e, n = Ar(t, "toString");
			if (typeof n == "function") {
				let e = n(t);
				return typeof e == "string" ? e : Tr(e);
			}
			return Tr(e);
		}
		default: return Tr(e);
	}
}
function Ar(e, t) {
	for (; e !== null;) {
		let n = ir(e, t);
		if (n) {
			if (n.get) return q(n.get);
			if (typeof n.value == "function") return q(n.value);
		}
		e = rr(e);
	}
	function n() {
		return null;
	}
	return n;
}
function jr(e) {
	try {
		return K(e, ""), !0;
	} catch {
		return !1;
	}
}
var Mr = U(/* @__PURE__ */ "a.abbr.acronym.address.area.article.aside.audio.b.bdi.bdo.big.blink.blockquote.body.br.button.canvas.caption.center.cite.code.col.colgroup.content.data.datalist.dd.decorator.del.details.dfn.dialog.dir.div.dl.dt.element.em.fieldset.figcaption.figure.font.footer.form.h1.h2.h3.h4.h5.h6.head.header.hgroup.hr.html.i.img.input.ins.kbd.label.legend.li.main.map.mark.marquee.menu.menuitem.meter.nav.nobr.ol.optgroup.option.output.p.picture.pre.progress.q.rp.rt.ruby.s.samp.search.section.select.shadow.slot.small.source.spacer.span.strike.strong.style.sub.summary.sup.table.tbody.td.template.textarea.tfoot.th.thead.time.tr.track.tt.u.ul.var.video.wbr".split(".")), Nr = U(/* @__PURE__ */ "svg.a.altglyph.altglyphdef.altglyphitem.animatecolor.animatemotion.animatetransform.circle.clippath.defs.desc.ellipse.enterkeyhint.exportparts.filter.font.g.glyph.glyphref.hkern.image.inputmode.line.lineargradient.marker.mask.metadata.mpath.part.path.pattern.polygon.polyline.radialgradient.rect.stop.style.switch.symbol.text.textpath.title.tref.tspan.view.vkern".split(".")), Pr = U([
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
]), Fr = U([
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
]), Ir = U(/* @__PURE__ */ "math.menclose.merror.mfenced.mfrac.mglyph.mi.mlabeledtr.mmultiscripts.mn.mo.mover.mpadded.mphantom.mroot.mrow.ms.mspace.msqrt.mstyle.msub.msup.msubsup.mtable.mtd.mtext.mtr.munder.munderover.mprescripts".split(".")), Lr = U([
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
]), Rr = U(["#text"]), zr = U(/* @__PURE__ */ "accept.action.align.alt.autocapitalize.autocomplete.autopictureinpicture.autoplay.background.bgcolor.border.capture.cellpadding.cellspacing.checked.cite.class.clear.color.cols.colspan.command.commandfor.controls.controlslist.coords.crossorigin.datetime.decoding.default.dir.disabled.disablepictureinpicture.disableremoteplayback.download.draggable.enctype.enterkeyhint.exportparts.face.for.headers.height.hidden.high.href.hreflang.id.inert.inputmode.integrity.ismap.kind.label.lang.list.loading.loop.low.max.maxlength.media.method.min.minlength.multiple.muted.name.nonce.noshade.novalidate.nowrap.open.optimum.part.pattern.placeholder.playsinline.popover.popovertarget.popovertargetaction.poster.preload.pubdate.radiogroup.readonly.rel.required.rev.reversed.role.rows.rowspan.spellcheck.scope.selected.shape.size.sizes.slot.span.srclang.start.src.srcset.step.style.summary.tabindex.title.translate.type.usemap.valign.value.width.wrap.xmlns".split(".")), Br = U(/* @__PURE__ */ "accent-height.accumulate.additive.alignment-baseline.amplitude.ascent.attributename.attributetype.azimuth.basefrequency.baseline-shift.begin.bias.by.class.clip.clippathunits.clip-path.clip-rule.color.color-interpolation.color-interpolation-filters.color-profile.color-rendering.cx.cy.d.dx.dy.diffuseconstant.direction.display.divisor.dominant-baseline.dur.edgemode.elevation.end.exponent.fill.fill-opacity.fill-rule.filter.filterunits.flood-color.flood-opacity.font-family.font-size.font-size-adjust.font-stretch.font-style.font-variant.font-weight.fx.fy.g1.g2.glyph-name.glyphref.gradientunits.gradienttransform.height.href.id.image-rendering.in.in2.intercept.k.k1.k2.k3.k4.kerning.keypoints.keysplines.keytimes.lang.lengthadjust.letter-spacing.kernelmatrix.kernelunitlength.lighting-color.local.marker-end.marker-mid.marker-start.markerheight.markerunits.markerwidth.maskcontentunits.maskunits.max.mask.mask-type.media.method.mode.min.name.numoctaves.offset.operator.opacity.order.orient.orientation.origin.overflow.paint-order.path.pathlength.patterncontentunits.patterntransform.patternunits.pointer-events.points.preservealpha.preserveaspectratio.primitiveunits.r.rx.ry.radius.refx.refy.repeatcount.repeatdur.restart.result.rotate.scale.seed.shape-rendering.slope.specularconstant.specularexponent.spreadmethod.startoffset.stddeviation.stitchtiles.stop-color.stop-opacity.stroke-dasharray.stroke-dashoffset.stroke-linecap.stroke-linejoin.stroke-miterlimit.stroke-opacity.stroke.stroke-width.style.surfacescale.systemlanguage.tabindex.tablevalues.targetx.targety.transform.transform-origin.text-anchor.text-decoration.text-orientation.text-rendering.textlength.type.u1.u2.unicode.values.vector-effect.viewbox.visibility.version.vert-adv-y.vert-origin-x.vert-origin-y.width.word-spacing.wrap.writing-mode.xchannelselector.ychannelselector.x.x1.x2.xmlns.y.y1.y2.z.zoomandpan".split(".")), Vr = U(/* @__PURE__ */ "accent.accentunder.align.bevelled.close.columnalign.columnlines.columnspacing.columnspan.denomalign.depth.dir.display.displaystyle.encoding.fence.frame.height.href.id.largeop.length.linethickness.lquote.lspace.mathbackground.mathcolor.mathsize.mathvariant.maxsize.minsize.movablelimits.notation.numalign.open.rowalign.rowlines.rowspacing.rowspan.rspace.rquote.scriptlevel.scriptminsize.scriptsizemultiplier.selection.separator.separators.stretchy.subscriptshift.supscriptshift.symmetric.voffset.width.xmlns".split(".")), Hr = U([
	"xlink:href",
	"xml:id",
	"xlink:title",
	"xml:space",
	"xmlns:xlink"
]), Ur = W(/{{[\w\W]*|^[\w\W]*}}/g), Wr = W(/<%[\w\W]*|^[\w\W]*%>/g), Gr = W(/\${[\w\W]*/g), Kr = W(/^data-[\-\w.\u00B7-\uFFFF]+$/), qr = W(/^aria-[\-\w]+$/), Jr = W(/^(?:(?:(?:f|ht)tps?|mailto|tel|callto|sms|cid|xmpp|matrix):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i), Yr = W(/^(?:\w+script|data):/i), Xr = W(/[\u0000-\u0020\u00A0\u1680\u180E\u2000-\u2029\u205F\u3000]/g), Zr = W(/^html$/i), Qr = W(/^[a-z][.\w]*(-[.\w]+)+$/i), $r = W(/<[/\w!]/g), ei = W(/<[/\w]/g), ti = W(/<\/no(script|embed|frames)/i), ni = W(/\/>/i), ri = {
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
}, ii = [
	"style",
	"script",
	"xmp",
	"iframe",
	"noembed",
	"noframes",
	"plaintext",
	"noscript"
], ai = U(J({}, ii)), oi = function() {
	let e = {};
	return lr(ii, (t) => {
		e[t] = W(RegExp("</" + t + "(?=[\\t\\n\\f\\r />])", "i"));
	}), U(e);
}(), si = function() {
	return typeof window > "u" ? null : window;
}, ci = function(e, t) {
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
}, li = function() {
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
}, ui = function(e, t, n, r) {
	return G(e, t) && mr(e[t]) ? J(r.base ? Y(r.base) : {}, e[t], r.transform) : n;
}, di = function(e, t, n) {
	let r = G(e, t) ? e[t] : void 0;
	return r && typeof r == "object" ? Y(r) : n();
};
function fi() {
	let e = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : si(), t = (e) => fi(e);
	if (t.version = "3.4.14", t.removed = [], !e || !e.document || e.document.nodeType !== ri.document || !e.Element) return t.isSupported = !1, t;
	let n = e.document, r = n, i = r.currentScript;
	e.DocumentFragment;
	let a = e.HTMLTemplateElement, o = e.Node, s = e.Element, c = e.NodeFilter;
	e.NamedNodeMap === void 0 && (e.NamedNodeMap || e.MozNamedAttrMap), e.HTMLFormElement;
	let l = e.DOMParser, u = e.trustedTypes, d = s.prototype, f = Ar(d, "cloneNode"), p = Ar(d, "remove"), m = Ar(d, "nextSibling"), h = Ar(d, "childNodes"), g = Ar(d, "parentNode"), _ = Ar(d, "shadowRoot"), v = Ar(d, "attributes"), y = o && o.prototype ? Ar(o.prototype, "nodeType") : null, b = o && o.prototype ? Ar(o.prototype, "nodeName") : null, x = o && o.prototype ? Ar(o.prototype, "ownerDocument") : null, S = function(e) {
		return y ? y(e) : e.nodeType;
	}, C = function(e) {
		return b ? b(e) : e.nodeName;
	};
	if (typeof a == "function") {
		let e = n.createElement("template");
		e.content && e.content.ownerDocument && (n = e.content.ownerDocument);
	}
	let w, T = "", E, ee = !1, D = 0, te = function() {
		if (D > 0) throw Er("A configured TRUSTED_TYPES_POLICY callback (createHTML or createScriptURL) must not call DOMPurify.sanitize, as that causes infinite recursion. Do not pass a policy whose callbacks wrap DOMPurify as TRUSTED_TYPES_POLICY; see the \"DOMPurify and Trusted Types\" section of the README.");
	}, O = function(e) {
		te(), D++;
		try {
			return w.createHTML(e);
		} finally {
			D--;
		}
	}, ne = function(e) {
		te(), D++;
		try {
			return w.createScriptURL(e);
		} finally {
			D--;
		}
	}, re = function() {
		return ee ||= (E = ci(u, i), !0), E;
	}, ie = n, ae = ie.implementation, oe = ie.createNodeIterator, se = ie.createDocumentFragment, ce = ie.getElementsByTagName, le = r.importNode, k = li();
	t.isSupported = typeof er == "function" && typeof g == "function" && ae && ae.createHTMLDocument !== void 0;
	let ue = Ur, de = Wr, fe = Gr, pe = Kr, me = qr, he = Yr, ge = Xr, _e = Qr, ve = Jr, A = null, j = J({}, [
		...Mr,
		...Nr,
		...Pr,
		...Ir,
		...Rr
	]), M = null, ye = J({}, [
		...zr,
		...Br,
		...Vr,
		...Hr
	]), be = Object.seal(ar(null, {
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
	})), xe = null, Se = null, Ce = Object.seal(ar(null, {
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
	})), we = !0, Te = !0, Ee = !1, De = !0, Oe = !1, ke = !0, Ae = !1, je = !1, Me = null, Ne = null, Pe = !1, Fe = !1, Ie = !1, Le = !1, Re = !0, ze = !1, Be = "user-content-", Ve = !0, He = !1, N = {}, Ue = null, We = J({}, /* @__PURE__ */ "annotation-xml.audio.colgroup.desc.foreignobject.head.iframe.math.mi.mn.mo.ms.mtext.noembed.noframes.noscript.plaintext.script.selectedcontent.style.svg.template.thead.title.video.xmp".split(".")), Ge = null, Ke = J({}, [
		"audio",
		"video",
		"img",
		"source",
		"image",
		"track"
	]), P = null, qe = J({}, [
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
	]), Je = "http://www.w3.org/1998/Math/MathML", Ye = "http://www.w3.org/2000/svg", Xe = "http://www.w3.org/1999/xhtml", Ze = Xe, Qe = !1, $e = null, F = J({}, [
		Je,
		Ye,
		Xe
	], gr), et = U([
		"mi",
		"mo",
		"mn",
		"ms",
		"mtext"
	]), I = J({}, et), tt = U(["annotation-xml"]), L = J({}, tt), nt = J({}, [
		"title",
		"style",
		"font",
		"a",
		"script"
	]), R = null, rt = ["application/xhtml+xml", "text/html"], z = null, it = null, at = n.createElement("form"), ot = function(e) {
		return e instanceof RegExp || e instanceof Function;
	}, st = function() {
		let e = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : {};
		if (it && it === e) return;
		(!e || typeof e != "object") && (e = {}), e = Y(e), R = rt.indexOf(e.PARSER_MEDIA_TYPE) === -1 ? "text/html" : e.PARSER_MEDIA_TYPE, z = R === "application/xhtml+xml" ? gr : hr, A = ui(e, "ALLOWED_TAGS", j, { transform: z }), M = ui(e, "ALLOWED_ATTR", ye, { transform: z }), $e = ui(e, "ALLOWED_NAMESPACES", F, { transform: gr }), P = ui(e, "ADD_URI_SAFE_ATTR", qe, {
			transform: z,
			base: qe
		}), Ge = ui(e, "ADD_DATA_URI_TAGS", Ke, {
			transform: z,
			base: Ke
		}), Ue = ui(e, "FORBID_CONTENTS", We, { transform: z }), xe = ui(e, "FORBID_TAGS", Y({}), { transform: z }), Se = ui(e, "FORBID_ATTR", Y({}), { transform: z }), N = G(e, "USE_PROFILES") ? e.USE_PROFILES && typeof e.USE_PROFILES == "object" ? Y(e.USE_PROFILES) : e.USE_PROFILES : !1, we = e.ALLOW_ARIA_ATTR !== !1, Te = e.ALLOW_DATA_ATTR !== !1, Ee = e.ALLOW_UNKNOWN_PROTOCOLS || !1, De = e.ALLOW_SELF_CLOSE_IN_ATTR !== !1, Oe = e.SAFE_FOR_TEMPLATES || !1, ke = e.SAFE_FOR_XML !== !1, Ae = e.WHOLE_DOCUMENT || !1, Fe = e.RETURN_DOM || !1, Ie = e.RETURN_DOM_FRAGMENT || !1, Le = e.RETURN_TRUSTED_TYPE || !1, Pe = e.FORCE_BODY || !1, Re = e.SANITIZE_DOM !== !1, ze = e.SANITIZE_NAMED_PROPS || !1, Ve = e.KEEP_CONTENT !== !1, He = e.IN_PLACE || !1, ve = jr(e.ALLOWED_URI_REGEXP) ? e.ALLOWED_URI_REGEXP : Jr, Ze = typeof e.NAMESPACE == "string" ? e.NAMESPACE : Xe, I = di(e, "MATHML_TEXT_INTEGRATION_POINTS", () => J({}, et)), L = di(e, "HTML_INTEGRATION_POINTS", () => J({}, tt));
		let t = di(e, "CUSTOM_ELEMENT_HANDLING", () => ar(null));
		if (be = ar(null), G(t, "tagNameCheck") && ot(t.tagNameCheck) && (be.tagNameCheck = t.tagNameCheck), G(t, "attributeNameCheck") && ot(t.attributeNameCheck) && (be.attributeNameCheck = t.attributeNameCheck), G(t, "allowCustomizedBuiltInElements") && typeof t.allowCustomizedBuiltInElements == "boolean" && (be.allowCustomizedBuiltInElements = t.allowCustomizedBuiltInElements), W(be), Oe && (Te = !1), Ie && (Fe = !0), N && (A = J({}, Rr), M = ar(null), N.html === !0 && (J(A, Mr), J(M, zr)), N.svg === !0 && (J(A, Nr), J(M, Br), J(M, Hr)), N.svgFilters === !0 && (J(A, Pr), J(M, Br), J(M, Hr)), N.mathMl === !0 && (J(A, Ir), J(M, Vr), J(M, Hr))), Ce.tagCheck = null, Ce.attributeCheck = null, G(e, "ADD_TAGS") && (typeof e.ADD_TAGS == "function" ? Ce.tagCheck = e.ADD_TAGS : mr(e.ADD_TAGS) && (A === j && (A = Y(A)), J(A, e.ADD_TAGS, z))), G(e, "ADD_ATTR") && (typeof e.ADD_ATTR == "function" ? Ce.attributeCheck = e.ADD_ATTR : mr(e.ADD_ATTR) && (M === ye && (M = Y(M)), J(M, e.ADD_ATTR, z))), G(e, "ADD_FORBID_CONTENTS") && mr(e.ADD_FORBID_CONTENTS) && (Ue === We && (Ue = Y(Ue)), J(Ue, e.ADD_FORBID_CONTENTS, z)), Ve && (A["#text"] = !0), Ae && J(A, [
			"html",
			"head",
			"body"
		]), A.table && (J(A, ["tbody"]), delete xe.tbody), e.TRUSTED_TYPES_POLICY) {
			if (typeof e.TRUSTED_TYPES_POLICY.createHTML != "function") throw Er("TRUSTED_TYPES_POLICY configuration option must provide a \"createHTML\" hook.");
			if (typeof e.TRUSTED_TYPES_POLICY.createScriptURL != "function") throw Er("TRUSTED_TYPES_POLICY configuration option must provide a \"createScriptURL\" hook.");
			let t = w;
			w = e.TRUSTED_TYPES_POLICY;
			try {
				T = O("");
			} catch (e) {
				throw w = t, e;
			}
		} else e.TRUSTED_TYPES_POLICY === null ? (w = void 0, T = "") : (w === void 0 && (w = re()), w && typeof T == "string" && (T = O("")));
		U && U(e), it = e;
	}, ct = J({}, [
		...Nr,
		...Pr,
		...Fr
	]), lt = J({}, [...Ir, ...Lr]), ut = function(e, t, n) {
		return t.namespaceURI === Xe ? e === "svg" : t.namespaceURI === Je ? e === "svg" && (n === "annotation-xml" || I[n]) : !!ct[e];
	}, dt = function(e, t, n) {
		return t.namespaceURI === Xe ? e === "math" : t.namespaceURI === Ye ? e === "math" && L[n] : !!lt[e];
	}, ft = function(e, t, n) {
		return t.namespaceURI === Ye && !L[n] || t.namespaceURI === Je && !I[n] ? !1 : !lt[e] && (nt[e] || !ct[e]);
	}, pt = function(e) {
		let t = g(e);
		(!t || !t.tagName) && (t = {
			namespaceURI: Ze,
			tagName: "template"
		});
		let n = hr(e.tagName), r = hr(t.tagName);
		return $e[e.namespaceURI] ? e.namespaceURI === Ye ? ut(n, t, r) : e.namespaceURI === Je ? dt(n, t, r) : e.namespaceURI === Xe ? ft(n, t, r) : !!(R === "application/xhtml+xml" && $e[e.namespaceURI]) : !1;
	}, mt = function(e) {
		fr(t.removed, { element: e });
		try {
			g(e).removeChild(e);
		} catch {
			if (p(e), !g(e)) throw Er("a node selected for removal could not be detached from its tree and cannot be safely returned; refusing to sanitize in place");
		}
	}, ht = function(e, t, n) {
		try {
			e.removeAttributeNode(t);
		} catch {
			try {
				e.removeAttribute(n);
			} catch {}
		}
	}, gt = function(e) {
		yt(e);
		let t = h(e);
		if (t) {
			let e = [];
			lr(t, (t) => {
				fr(e, t);
			}), lr(e, (e) => {
				try {
					p(e);
				} catch {}
			});
		}
		let n = v(e);
		if (n) for (let t = n.length - 1; t >= 0; --t) {
			let r = n[t], i = r && r.name;
			typeof i == "string" && ht(e, r, i);
		}
	}, _t = function(e, n, r) {
		if (!r) try {
			r = n.getAttributeNode(e);
		} catch {
			r = null;
		}
		fr(t.removed, {
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
			if (Fe || Ie) try {
				mt(n);
			} catch {}
			else try {
				n.setAttribute(e, "");
			} catch {}
		}
	}, vt = function(e) {
		let t = v(e);
		if (t) for (let n = t.length - 1; n >= 0; --n) {
			let r = t[n], i = r && r.name;
			typeof i != "string" || M[z(i)] || ht(e, r, i);
		}
	}, yt = function(e) {
		let t = [e];
		for (; t.length > 0;) {
			let e = t.pop();
			S(e) === ri.element && vt(e);
			let n = h(e);
			if (n) for (let e = n.length - 1; e >= 0; --e) t.push(n[e]);
		}
	}, bt = function(e, t) {
		return ke ? e === "patchsrc" || e === "for" && t !== "label" && t !== "output" : !1;
	}, xt = function(e) {
		if (!ke) return;
		let t = [e];
		for (; t.length > 0;) {
			let e = t.pop(), n = S(e);
			if (n === ri.processingInstruction || n === ri.comment && K(ei, e.data)) {
				try {
					p(e);
				} catch {}
				continue;
			}
			if (n === ri.element) {
				let t = e, n = z(C(e));
				try {
					t.hasAttribute && t.hasAttribute("patchsrc") && t.removeAttribute("patchsrc"), t.hasAttribute && t.hasAttribute("for") && bt("for", n) && t.removeAttribute("for");
				} catch {}
			}
			let r = h(e);
			if (r) for (let e = r.length - 1; e >= 0; --e) t.push(r[e]);
		}
	}, St = function(e) {
		let t = null, r = null;
		if (Pe) e = "<remove></remove>" + e;
		else {
			let t = _r(e, /^[\r\n\t ]+/);
			r = t && t[0];
		}
		R === "application/xhtml+xml" && Ze === Xe && (e = "<html xmlns=\"http://www.w3.org/1999/xhtml\"><head></head><body>" + e + "</body></html>");
		let i = w ? O(e) : e;
		if (Ze === Xe) try {
			t = new l().parseFromString(i, R);
		} catch {}
		if (!t || !t.documentElement) {
			t = ae.createDocument(Ze, "template", null);
			try {
				t.documentElement.innerHTML = Qe ? T : i;
			} catch {}
		}
		let a = t.body || t.documentElement;
		return e && r && a.insertBefore(n.createTextNode(r), a.childNodes[0] || null), Ze === Xe ? ce.call(t, Ae ? "html" : "body")[0] : Ae ? t.documentElement : a;
	}, Ct = function(e) {
		let t = x ? x(e) : e.ownerDocument;
		return oe.call(t || e, e, c.SHOW_ELEMENT | c.SHOW_COMMENT | c.SHOW_TEXT | c.SHOW_PROCESSING_INSTRUCTION | c.SHOW_CDATA_SECTION, null);
	}, wt = function(e) {
		return e = vr(e, ue, " "), e = vr(e, de, " "), e = vr(e, fe, " "), e;
	}, Tt = function(e) {
		e.normalize();
		let t = x ? x(e) : e.ownerDocument, n = oe.call(t || e, e, c.SHOW_TEXT | c.SHOW_COMMENT | c.SHOW_CDATA_SECTION | c.SHOW_PROCESSING_INSTRUCTION, null), r = n.nextNode();
		for (; r;) r.data = wt(r.data), r = n.nextNode();
		let i = e.querySelectorAll?.call(e, "template");
		i && lr(i, (e) => {
			Dt(e.content) && Tt(e.content);
		});
	}, Et = function(e) {
		let t = b ? b(e) : null;
		return typeof t != "string" || z(t) !== "form" ? !1 : typeof e.nodeName != "string" || typeof e.textContent != "string" || typeof e.removeChild != "function" || e.attributes !== v(e) || typeof e.removeAttribute != "function" || typeof e.setAttribute != "function" || typeof e.namespaceURI != "string" || typeof e.insertBefore != "function" || typeof e.hasChildNodes != "function" || e.nodeType !== y(e) || e.childNodes !== h(e);
	}, Dt = function(e) {
		if (!y || typeof e != "object" || !e) return !1;
		try {
			return y(e) === ri.documentFragment;
		} catch {
			return !1;
		}
	}, Ot = function(e) {
		if (!y || typeof e != "object" || !e) return !1;
		try {
			return typeof y(e) == "number";
		} catch {
			return !1;
		}
	};
	function kt(e, n, r) {
		e.length !== 0 && lr(e, (e) => {
			e.call(t, n, r, it);
		});
	}
	let At = function(e, t) {
		return !!(ke && e.hasChildNodes() && !Ot(e.firstElementChild) && K($r, e.textContent) && K($r, e.innerHTML) || ke && e.namespaceURI === Xe && ai[t] && (Ot(e.firstElementChild) || typeof e.textContent == "string" && K(oi[t], e.textContent)) || e.nodeType === ri.processingInstruction || ke && e.nodeType === ri.comment && K(ei, e.data));
	}, jt = function(e, t) {
		return e instanceof RegExp ? K(e, t) : e instanceof Function && !!e(t, ...[...arguments].slice(2));
	}, Mt = function(e, t, n) {
		if (!xe[t] && Rt(t) && jt(be.tagNameCheck, t)) return !1;
		if (Ve && !Ue[t]) {
			let t = g(e), r = h(e);
			if (r && t) {
				let i = r.length;
				for (let a = i - 1; a >= 0; --a) {
					let i = e === n ? f(r[a], !0) : r[a];
					t.insertBefore(i, m(e));
				}
			}
		}
		return mt(e), !0;
	}, Nt = function(e, t, n, r) {
		return e.length === 0 ? t : t === n || t === r ? Y(t) : t;
	}, Pt = function(e, t) {
		return e === t || g(e) !== null ? !1 : (He && yt(e), !0);
	}, Ft = function(e, n) {
		if (kt(k.beforeSanitizeElements, e, null), Pt(e, n)) return !0;
		if (Et(e)) return mt(e), !0;
		let r = z(C(e));
		if (A = Nt(k.uponSanitizeElement, A, j, Me), kt(k.uponSanitizeElement, e, {
			tagName: r,
			allowedTags: A
		}), Pt(e, n)) return !0;
		if (At(e, r)) return mt(e), !0;
		if (xe[r] || !(Ce.tagCheck instanceof Function && Ce.tagCheck(r)) && !A[r]) {
			let t = Mt(e, r, n);
			return t === !1 && kt(k.afterSanitizeElements, e, null), t;
		}
		if (S(e) === ri.element && !pt(e) || (r === "noscript" || r === "noembed" || r === "noframes") && K(ti, e.innerHTML)) return mt(e), !0;
		if (Oe && e.nodeType === ri.text) {
			let n = wt(e.textContent);
			e.textContent !== n && (fr(t.removed, { element: e.cloneNode() }), e.textContent = n);
		}
		return kt(k.afterSanitizeElements, e, null), !1;
	}, It = function(e, t, r) {
		if (Se[t] || bt(t, e) || Re && (t === "id" || t === "name") && (r in n || r in at)) return !1;
		let i = M[t] || Ce.attributeCheck instanceof Function && Ce.attributeCheck(t, e);
		return Te && K(pe, t) || we && K(me, t) ? !0 : i ? P[t] || K(ve, vr(r, ge, "")) || (t === "src" || t === "xlink:href" || t === "href") && e !== "script" && yr(r, "data:") === 0 && Ge[e] || Ee && !K(he, vr(r, ge, "")) ? !0 : !r : Rt(e) && jt(be.tagNameCheck, e) && jt(be.attributeNameCheck, t, e) || t === "is" && be.allowCustomizedBuiltInElements && jt(be.tagNameCheck, r);
	}, Lt = J({}, [
		"annotation-xml",
		"color-profile",
		"font-face",
		"font-face-format",
		"font-face-name",
		"font-face-src",
		"font-face-uri",
		"missing-glyph"
	]), Rt = function(e) {
		return !Lt[hr(e)] && K(_e, e);
	}, zt = function(e, t, n, r) {
		if (w && typeof u == "object" && typeof u.getAttributeType == "function" && !n) switch (u.getAttributeType(e, t)) {
			case "TrustedHTML": return O(r);
			case "TrustedScriptURL": return ne(r);
		}
		return r;
	}, Bt = function(e, n, r, i) {
		try {
			r ? e.setAttributeNS(r, n, i) : e.setAttribute(n, i), Et(e) ? mt(e) : dr(t.removed);
		} catch {
			_t(n, e);
		}
	}, Vt = function(e) {
		kt(k.beforeSanitizeAttributes, e, null);
		let t = e.attributes;
		if (!t || Et(e)) return;
		M = Nt(k.uponSanitizeAttribute, M, ye, Ne);
		let n = {
			attrName: "",
			attrValue: "",
			keepAttr: !0,
			allowedAttributes: M,
			forceKeepAttr: void 0
		}, r = t.length, i = z(e.nodeName);
		for (; r--;) {
			let a = t[r], o = a.name, s = a.namespaceURI, c = a.value, l = z(o), u = c, d = o === "value" ? u : br(u);
			if (n.attrName = l, n.attrValue = d, n.keepAttr = !0, n.forceKeepAttr = void 0, kt(k.uponSanitizeAttribute, e, n), d = n.attrValue, ze && (l === "id" || l === "name") && yr(d, Be) !== 0 && (_t(o, e, a), d = Be + d), ke && K(/((--!?|])>)|<\/(style|script|title|xmp|textarea|noscript|iframe|noembed|noframes)/i, d)) {
				_t(o, e, a);
				continue;
			}
			if (l === "attributename" && _r(d, "href")) {
				_t(o, e, a);
				continue;
			}
			if (!n.forceKeepAttr) {
				if (!n.keepAttr) {
					_t(o, e, a);
					continue;
				}
				if (!De && K(ni, d)) {
					_t(o, e, a);
					continue;
				}
				if (Oe && (d = wt(d)), !It(i, l, d)) {
					_t(o, e, a);
					continue;
				}
				d = zt(i, l, s, d), d !== u && Bt(e, o, s, d);
			}
		}
		kt(k.afterSanitizeAttributes, e, null);
	}, Ht = function(e) {
		let t = null, n = Ct(e);
		for (kt(k.beforeSanitizeShadowDOM, e, null); t = n.nextNode();) if (kt(k.uponSanitizeShadowNode, t, null), Ft(t, e), Vt(t), Dt(t.content) && Ht(t.content), S(t) === ri.element) {
			let e = _(t);
			Dt(e) && (Ut(e), Ht(e));
		}
		kt(k.afterSanitizeShadowDOM, e, null);
	}, Ut = function(e) {
		let t = [{
			node: e,
			shadow: null
		}];
		for (; t.length > 0;) {
			let e = t.pop();
			if (e.shadow) {
				Ht(e.shadow);
				continue;
			}
			let n = e.node, r = S(n) === ri.element, i = h(n);
			if (i) for (let e = i.length - 1; e >= 0; --e) t.push({
				node: i[e],
				shadow: null
			});
			if (r) {
				let e = b ? b(n) : null;
				if (typeof e == "string" && z(e) === "template") {
					let e = n.content;
					Dt(e) && t.push({
						node: e,
						shadow: null
					});
				}
			}
			if (r) {
				let e = _(n);
				Dt(e) && t.push({
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
		if (Qe = !e, Qe && (e = "<!-->"), typeof e != "string" && !Ot(e) && (e = kr(e), typeof e != "string")) throw Er("dirty is not a string, aborting");
		if (!t.isSupported) return e;
		je ? (A = Me, M = Ne) : st(n), (k.uponSanitizeElement.length > 0 || k.uponSanitizeAttribute.length > 0) && (A = Y(A)), k.uponSanitizeAttribute.length > 0 && (M = Y(M)), t.removed = [];
		let c = He && typeof e != "string" && Ot(e);
		if (c) {
			xt(e);
			let t = C(e);
			if (typeof t == "string") {
				let n = z(t);
				if (!A[n] || xe[n]) throw gt(e), Er("root node is forbidden and cannot be sanitized in-place");
			}
			if (Et(e)) throw gt(e), Er("root node is clobbered and cannot be sanitized in-place");
			try {
				Ut(e);
			} catch (t) {
				throw gt(e), t;
			}
		} else if (Ot(e)) i = St("<!---->"), a = i.ownerDocument.importNode(e, !0), a.nodeType === ri.element && a.nodeName === "BODY" || a.nodeName === "HTML" ? i = a : i.appendChild(a), Ut(a);
		else {
			if (!Fe && !Oe && !Ae && e.indexOf("<") === -1) return w && Le ? O(e) : e;
			if (i = St(e), !i) return Fe ? null : Le ? T : "";
		}
		i && Pe && mt(i.firstChild);
		let l = c ? e : i;
		try {
			let e = Ct(l);
			for (; o = e.nextNode();) Ft(o, l), Vt(o), Dt(o.content) && Ht(o.content);
		} catch (n) {
			throw c && (gt(e), lr(t.removed, (e) => {
				e.element && yt(e.element);
			})), n;
		}
		if (c) return lr(t.removed, (e) => {
			e.element && yt(e.element);
		}), Oe && Tt(e), e;
		if (Fe) {
			if (Oe && Tt(i), Ie) for (s = se.call(i.ownerDocument); i.firstChild;) s.appendChild(i.firstChild);
			else s = i;
			return (M.shadowroot || M.shadowrootmode) && (s = le.call(r, s, !0)), s;
		}
		let u = Ae ? i.outerHTML : i.innerHTML;
		return Ae && A["!doctype"] && i.ownerDocument && i.ownerDocument.doctype && i.ownerDocument.doctype.name && K(Zr, i.ownerDocument.doctype.name) && (u = "<!DOCTYPE " + i.ownerDocument.doctype.name + ">\n" + u), Oe && (u = wt(u)), w && Le ? O(u) : u;
	}, t.setConfig = function() {
		let e = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : {};
		st(e), je = !0, Me = A, Ne = M;
	}, t.clearConfig = function() {
		it = null, je = !1, Me = null, Ne = null, w = E, T = "";
	}, t.isValidAttribute = function(e, t, n) {
		it || st({});
		let r = z(e), i = z(t);
		return It(r, i, n);
	}, t.addHook = function(e, t) {
		typeof t == "function" && G(k, e) && fr(k[e], t);
	}, t.removeHook = function(e, t) {
		if (G(k, e)) {
			if (t !== void 0) {
				let n = ur(k[e], t);
				return n === -1 ? void 0 : pr(k[e], n, 1)[0];
			}
			return dr(k[e]);
		}
	}, t.removeHooks = function(e) {
		G(k, e) && (k[e] = []);
	}, t.removeAllHooks = function() {
		k = li();
	}, t;
}
var pi = fi();
//#endregion
//#region node_modules/.pnpm/marked@18.0.10/node_modules/marked/lib/marked.esm.js
function mi() {
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
var hi = mi();
function gi(e) {
	hi = e;
}
var _i = { exec: () => null };
function vi(e) {
	let t = [];
	return (n) => {
		let r = Math.max(0, Math.min(3, n - 1)), i = t[r];
		return i || (i = e(r), t[r] = i), i;
	};
}
function X(e, t = "") {
	let n = typeof e == "string" ? e : e.source, r = {
		replace: (e, t) => {
			let i = typeof t == "string" ? t : t.source;
			return i = i.replace(Z.caret, "$1"), n = n.replace(e, i), r;
		},
		getRegex: () => new RegExp(n, t)
	};
	return r;
}
var yi = ((e = "") => {
	try {
		return !!RegExp("(?<=1)(?<!1)" + e);
	} catch {
		return !1;
	}
})(), Z = {
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
	nextBulletRegex: vi((e) => RegExp(`^ {0,${e}}(?:[*+-]|\\d{1,9}[.)])((?:[ 	][^\\n]*)?(?:\\n|$))`)),
	hrRegex: vi((e) => RegExp(`^ {0,${e}}((?:- *){3,}|(?:_ *){3,}|(?:\\* *){3,})(?:\\n+|$)`)),
	fencesBeginRegex: vi((e) => RegExp(`^ {0,${e}}(?:\`\`\`|~~~)`)),
	headingBeginRegex: vi((e) => RegExp(`^ {0,${e}}#`)),
	htmlBeginRegex: vi((e) => RegExp(`^ {0,${e}}<(?:[a-z].*>|!--)`, "i")),
	blockquoteBeginRegex: vi((e) => RegExp(`^ {0,${e}}>`))
}, bi = /^(?:[ \t]*(?:\n|$))+/, xi = /^((?: {4}| {0,3}\t)[^\n]+(?:\n(?:[ \t]*(?:\n|$))*)?)+/, Si = /^ {0,3}(`{3,}(?=[^`\n]*(?:\n|$))|~{3,})([^\n]*)(?:\n|$)(?:|([\s\S]*?)(?:\n|$))(?: {0,3}\1[~`]* *(?=\n|$)|$)/, Ci = /^ {0,3}((?:-[\t ]*){3,}|(?:_[ \t]*){3,}|(?:\*[ \t]*){3,})(?:\n+|$)/, wi = /^ {0,3}(#{1,6})(?=\s|$)(.*)(?:\n+|$)/, Ti = / {0,3}(?:[*+-]|\d{1,9}[.)])/, Ei = /^(?!bull |blockCode|fences|blockquote|heading|html|table)((?:.|\n(?!\s*?\n|bull |blockCode|fences|blockquote|heading|html|table))+?)\n {0,3}(=+|-+) *(?:\n+|$)/, Di = X(Ei).replace(/bull/g, Ti).replace(/blockCode/g, /(?: {4}| {0,3}\t)/).replace(/fences/g, / {0,3}(?:`{3,}|~{3,})/).replace(/blockquote/g, / {0,3}>/).replace(/heading/g, / {0,3}#{1,6}(?:\s|$)/).replace(/html/g, / {0,3}<[^\n>]+>\n/).replace(/\|table/g, "").getRegex(), Oi = X(Ei).replace(/bull/g, Ti).replace(/blockCode/g, /(?: {4}| {0,3}\t)/).replace(/fences/g, / {0,3}(?:`{3,}|~{3,})/).replace(/blockquote/g, / {0,3}>/).replace(/heading/g, / {0,3}#{1,6}(?:\s|$)/).replace(/html/g, / {0,3}<[^\n>]+>\n/).replace(/table/g, / {0,3}\|?(?:[:\- ]*\|)+[\:\- ]*\n/).getRegex(), ki = /^([^\n]+(?:\n(?!hr|heading|lheading|blockquote|fences|list|html|table|[ \t]+\n)[^\n]+)*)/, Ai = /^[^\n]+/, ji = /(?!\s*\])(?:\\[\s\S]|[^\[\]\\])+/, Mi = X(/^ {0,3}\[(label)\]: *(?:\n[ \t]*)?([^<\s][^\s]*|<.*?>)(?:(?: +(?:\n[ \t]*)?| *\n[ \t]*)(title))? *(?:\n+|$)/).replace("label", ji).replace("title", /(?:"(?:\\"?|[^"\\])*"|'[^'\n]*(?:\n[^'\n]+)*\n?'|\([^()]*\))/).getRegex(), Ni = X(/^(bull)([ \t][^\n]*?)?(?:\n|$)/).replace(/bull/g, Ti).getRegex(), Pi = "address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|frameset|h[1-6]|head|header|hr|html|iframe|legend|li|link|main|menu|menuitem|meta|nav|noframes|ol|optgroup|option|p|param|search|section|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul", Fi = /<!--(?:-?>|[\s\S]*?(?:-->|$))/, Ii = X("^ {0,3}(?:<(script|pre|style|textarea)[\\s>][\\s\\S]*?(?:</\\1>[^\\n]*\\n*|$)|comment[^\\n]*(\\n+|$)|<\\?[\\s\\S]*?(?:\\?>[^\\n]*\\n*|$)|<![A-Z][\\s\\S]*?(?:>[^\\n]*\\n*|$)|<!\\[CDATA\\[[\\s\\S]*?(?:\\]\\]>[^\\n]*\\n*|$)|</?(tag)(?: +|\\n|/?>)[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$)|<(?!script|pre|style|textarea)([a-z][\\w-]*)(?:attribute)*? */?>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$)|</(?!script|pre|style|textarea)[a-z][\\w-]*\\s*>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$))", "i").replace("comment", Fi).replace("tag", Pi).replace("attribute", / +[a-zA-Z:_][\w.:-]*(?: *= *"[^"\n]*"| *= *'[^'\n]*'| *= *[^\s"'=<>`]+)?/).getRegex(), Li = (e) => X(ki).replace("hr", Ci).replace("heading", " {0,3}#{1,6}(?:\\s|$)").replace("|lheading", "").replace("|table", "").replace("blockquote", " {0,3}>").replace("fences", " {0,3}(?:`{3,}(?=[^`\\n]*(?:\\n|$))|~~~)[^\\n]*(?:\\n|$)").replace("list", e).replace("html", "</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag", Pi).getRegex(), Ri = Li(/ {0,3}(?:[*+-]|1[.)])[ \t]+[^ \t\n]/), zi = Li(/ {0,3}(?:[*+-]|\d{1,9}[.)])(?:[ \t]|\n|$)/), Bi = {
	blockquote: X(/^( {0,3}> ?(paragraph|[^\n]*)(?:\n|$))+/).replace("paragraph", zi).getRegex(),
	code: xi,
	def: Mi,
	fences: Si,
	heading: wi,
	hr: Ci,
	html: Ii,
	lheading: Di,
	list: Ni,
	newline: bi,
	paragraph: Ri,
	table: _i,
	text: Ai
}, Vi = X("^ *([^\\n ].*)\\n {0,3}((?:\\| *)?:?-+:? *(?:\\| *:?-+:? *)*(?:\\| *)?)(?:\\n((?:(?! *\\n|hr|heading|blockquote|code|fences|list|html).*(?:\\n|$))*)\\n*|$)").replace("hr", Ci).replace("heading", " {0,3}#{1,6}(?:\\s|$)").replace("blockquote", " {0,3}>").replace("code", "(?: {4}| {0,3}	)[^\\n]").replace("fences", " {0,3}(?:`{3,}(?=[^`\\n]*(?:\\n|$))|~~~)[^\\n]*(?:\\n|$)").replace("list", " {0,3}(?:[*+-]|1[.)])[ \\t]").replace("html", "</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag", Pi).getRegex(), Hi = {
	...Bi,
	lheading: Oi,
	table: Vi,
	paragraph: X(ki).replace("hr", Ci).replace("heading", " {0,3}#{1,6}(?:\\s|$)").replace("|lheading", "").replace("table", Vi).replace("blockquote", " {0,3}>").replace("fences", " {0,3}(?:`{3,}(?=[^`\\n]*(?:\\n|$))|~~~)[^\\n]*(?:\\n|$)").replace("list", " {0,3}(?:[*+-]|1[.)])[ \\t]+[^ \\t\\n]").replace("html", "</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag", Pi).getRegex()
}, Ui = {
	...Bi,
	html: X("^ *(?:comment *(?:\\n|\\s*$)|<(tag)[\\s\\S]+?</\\1> *(?:\\n{2,}|\\s*$)|<tag(?:\"[^\"]*\"|'[^']*'|\\s[^'\"/>\\s]*)*?/?> *(?:\\n{2,}|\\s*$))").replace("comment", Fi).replace(/tag/g, "(?!(?:a|em|strong|small|s|cite|q|dfn|abbr|data|time|code|var|samp|kbd|sub|sup|i|b|u|mark|ruby|rt|rp|bdi|bdo|span|br|wbr|ins|del|img)\\b)\\w+(?!:|[^\\w\\s@]*@)\\b").getRegex(),
	def: /^ *\[([^\]]+)\]: *<?([^\s>]+)>?(?: +(["(][^\n]+[")]))? *(?:\n+|$)/,
	heading: /^(#{1,6})(.*)(?:\n+|$)/,
	fences: _i,
	lheading: /^(.+?)\n {0,3}(=+|-+) *(?:\n+|$)/,
	paragraph: X(ki).replace("hr", Ci).replace("heading", " *#{1,6} *[^\n]").replace("lheading", Di).replace("|table", "").replace("blockquote", " {0,3}>").replace("|fences", "").replace("|list", "").replace("|html", "").replace("|tag", "").getRegex()
}, Wi = /^\\([!"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])/, Gi = /^(`+)([^`]|[^`][\s\S]*?[^`])\1(?!`)/, Ki = /^( {2,}|\\)\n(?!\s*$)/, qi = /^(`+|[^`])(?:(?= {2,}\n)|[\s\S]*?(?:(?=[\\<!\[`*_]|\b_|$)|[^ ](?= {2,}\n)))/, Ji = /[\p{P}\p{S}]/u, Yi = /[\s\p{P}\p{S}]/u, Xi = /[^\s\p{P}\p{S}]/u, Zi = X(/^((?![*_])punctSpace)/, "u").replace(/punctSpace/g, Yi).getRegex(), Qi = /[\p{Pi}\p{Ps}"']/u, $i = /(?!~)[\p{P}\p{S}]/u, ea = /(?!~)[\s\p{P}\p{S}]/u, ta = /(?:[^\s\p{P}\p{S}]|~)/u, na = X(/link|precode-code|html/, "g").replace("link", /\[(?:[^\[\]`]|(?<a>`+)[^`]+\k<a>(?!`))*?\]\((?:\\[\s\S]|[^\\\(\)]|\((?:\\[\s\S]|[^\\\(\)])*\))*\)/).replace("precode-", yi ? "(?<!`)()" : "(^^|[^`])").replace("code", /(?<b>`+)[^`]+\k<b>(?!`)/).replace("html", /<(?! )[^<>]*?>/).getRegex(), ra = /^(?:\*+(?:((?!\*)punct)|([^\s*]))?)|^_+(?:((?!_)punct)|([^\s_]))?/, ia = X(ra, "u").replace(/punct/g, Ji).getRegex(), aa = X(ra, "u").replace(/punct/g, $i).getRegex(), oa = X(/^(?:\*+(?:((?!\*)(?!openQuote)punct)|([^\s*]))?)|^_+(?:((?!_)(?!openQuote)punct)|([^\s_]))?/, "u").replace(/openQuote/g, Qi).replace(/punct/g, Ji).getRegex(), sa = "^[^_*]*?__[^_*]*?\\*[^_*]*?(?=__)|[^*]+(?=[^*])|(?!\\*)punct(\\*+)(?=[\\s]|$)|notPunctSpace(\\*+)(?!\\*)(?=punctSpace|$)|(?!\\*)punctSpace(\\*+)(?=notPunctSpace)|[\\s](\\*+)(?!\\*)(?=punct)|(?!\\*)punct(\\*+)(?!\\*)(?=punct)|notPunctSpace(\\*+)(?=notPunctSpace)", ca = X(sa, "gu").replace(/notPunctSpace/g, Xi).replace(/punctSpace/g, Yi).replace(/punct/g, Ji).getRegex(), la = X(sa, "gu").replace(/notPunctSpace/g, ta).replace(/punctSpace/g, ea).replace(/punct/g, $i).getRegex(), ua = X("^[^_*]*?__[^_*]*?\\*[^_*]*?(?=__)|[^*]+(?=[^*])|(?!\\*)punct(\\*+)(?=[\\s]|$)|notPunctSpace(\\*+)(?!\\*)(?=punctSpace|$)|(?!\\*)[\\s](\\*+)(?=notPunctSpace)|[\\s](\\*+)(?!\\*)(?=punct)|(?!\\*)punct(\\*+)(?!\\*)(?=punct)|(?:(?!\\*)punct|notPunctSpace)(\\*+)(?!\\*)(?=notPunctSpace)", "gu").replace(/notPunctSpace/g, Xi).replace(/punctSpace/g, Yi).replace(/punct/g, Ji).getRegex(), da = X("^[^_*]*?\\*\\*[^_*]*?_[^_*]*?(?=\\*\\*)|[^_]+(?=[^_])|(?!_)punct(_+)(?=[\\s]|$)|notPunctSpace(_+)(?!_)(?=punctSpace|$)|(?!_)punctSpace(_+)(?=notPunctSpace)|[\\s](_+)(?!_)(?=punct)|(?!_)punct(_+)(?!_)(?=punct)", "gu").replace(/notPunctSpace/g, Xi).replace(/punctSpace/g, Yi).replace(/punct/g, Ji).getRegex(), fa = X("^[^_*]*?\\*\\*[^_*]*?_[^_*]*?(?=\\*\\*)|[^_]+(?=[^_])|(?!_)punct(_+)(?=[\\s]|$)|notPunctSpace(_+)(?!_)(?=punctSpace|$)|(?!_)[\\s](_+)(?=notPunctSpace)|[\\s](_+)(?!_)(?=punct)|(?!_)punct(_+)(?!_)(?=punct)|(?:(?!_)punct|notPunctSpace)(_+)(?!_)(?=notPunctSpace)", "gu").replace(/notPunctSpace/g, Xi).replace(/punctSpace/g, Yi).replace(/punct/g, Ji).getRegex(), pa = X(/^~~?(?:((?!~)punct)|[^\s~])/, "u").replace(/punct/g, Ji).getRegex(), ma = X("^[^~]+(?=[^~])|(?!~)punct(~~?)(?=[\\s]|$)|notPunctSpace(~~?)(?!~)(?=punctSpace|$)|(?!~)punctSpace(~~?)(?=notPunctSpace)|[\\s](~~?)(?!~)(?=punct)|(?!~)punct(~~?)(?!~)(?=punct)|notPunctSpace(~~?)(?=notPunctSpace)", "gu").replace(/notPunctSpace/g, Xi).replace(/punctSpace/g, Yi).replace(/punct/g, Ji).getRegex(), ha = X(/\\(punct)/, "gu").replace(/punct/g, Ji).getRegex(), ga = X(/^<(scheme:[^\s\x00-\x1f<>]*|email)>/).replace("scheme", /[a-zA-Z][a-zA-Z0-9+.-]{1,31}/).replace("email", /[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+(@)[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+(?![-_])/).getRegex(), _a = X(Fi).replace("(?:-->|$)", "-->").getRegex(), va = X("^comment|^</[a-zA-Z][\\w:-]*\\s*>|^<[a-zA-Z][\\w-]*(?:attribute)*?\\s*/?>|^<\\?[\\s\\S]*?\\?>|^<![a-zA-Z]+\\s[\\s\\S]*?>|^<!\\[CDATA\\[[\\s\\S]*?\\]\\]>").replace("comment", _a).replace("attribute", /\s+[a-zA-Z:_][\w.:-]*(?:\s*=\s*"[^"]*"|\s*=\s*'[^']*'|\s*=\s*[^\s"'=<>`]+)?/).getRegex(), ya = /(?:\[(?:\\[\s\S]|[^\[\]\\])*\]|\\[\s\S]|`+(?!`)[^`]*?`+(?!`)|``+(?=\])|[^\[\]\\`])*?/, ba = X(/^!?\[(label)\]\(\s*(href)(?:(?:[ \t]+(?:\n[ \t]*)?|\n[ \t]*)(title))?\s*\)/).replace("label", ya).replace("href", /<(?:\\.|[^\n<>\\])+>|[^ \t\n\x00-\x1f]+|(?=\))/).replace("title", /"(?:\\"?|[^"\\])*"|'(?:\\'?|[^'\\])*'|\((?:\\\)?|[^)\\])*\)/).getRegex(), xa = X(/^!?\[(label)\]\[(ref)\]/).replace("label", ya).replace("ref", ji).getRegex(), Sa = X(/^!?\[(ref)\](?:\[\])?/).replace("ref", ji).getRegex(), Ca = X("reflink|nolink(?!\\()", "g").replace("reflink", xa).replace("nolink", Sa).getRegex(), wa = /[hH][tT][tT][pP][sS]?|[fF][tT][pP]/, Ta = {
	_backpedal: _i,
	anyPunctuation: ha,
	autolink: ga,
	blockSkip: na,
	br: Ki,
	code: Gi,
	del: _i,
	delLDelim: _i,
	delRDelim: _i,
	emStrongLDelim: ia,
	emStrongRDelimAst: ca,
	emStrongRDelimUnd: da,
	escape: Wi,
	link: ba,
	nolink: Sa,
	punctuation: Zi,
	reflink: xa,
	reflinkSearch: Ca,
	tag: va,
	text: qi,
	url: _i
}, Ea = {
	...Ta,
	emStrongLDelim: oa,
	emStrongRDelimAst: ua,
	emStrongRDelimUnd: fa,
	link: X(/^!?\[(label)\]\((.*?)\)/).replace("label", ya).getRegex(),
	reflink: X(/^!?\[(label)\]\s*\[([^\]]*)\]/).replace("label", ya).getRegex()
}, Da = {
	...Ta,
	emStrongRDelimAst: la,
	emStrongLDelim: aa,
	delLDelim: pa,
	delRDelim: ma,
	url: X(/^((?:protocol):\/\/|www\.)(?:[a-zA-Z0-9\-]+\.?)+[^\s<]*|^email/).replace("protocol", wa).replace("email", /[A-Za-z0-9._+-]+(@)[a-zA-Z0-9-_]+(?:\.[a-zA-Z0-9-_]*[a-zA-Z0-9])+(?![-_])/).getRegex(),
	_backpedal: /(?:[^?!.,:;*_'"~()&]+|\([^)]*\)|&(?![a-zA-Z0-9]+;$)|[?!.,:;*_'"~)]+(?!$))+/,
	del: /^(~~?)(?=[^\s~])((?:\\[\s\S]|[^\\])*?(?:\\[\s\S]|[^\s~\\]))\1(?=[^~]|$)/,
	text: X(/^(`+|~+|[^`~])(?:(?=[`~])|(?= {2,}\n)|(?=[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@)|[\s\S]*?(?:(?=[\\<!\[`*~_]|\b_|protocol:\/\/|www\.|$)|[^ ](?= {2,}\n)|[^a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-](?=[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@)))/).replace("protocol", wa).getRegex()
}, Oa = {
	...Da,
	br: X(Ki).replace("{2,}", "*").getRegex(),
	text: X(Da.text).replace("\\b_", "\\b_| {2,}\\n").replace(/\{2,\}/g, "*").getRegex()
}, ka = {
	normal: Bi,
	gfm: Hi,
	pedantic: Ui
}, Aa = {
	normal: Ta,
	gfm: Da,
	breaks: Oa,
	pedantic: Ea
}, ja = {
	"&": "&amp;",
	"<": "&lt;",
	">": "&gt;",
	"\"": "&quot;",
	"'": "&#39;"
}, Ma = (e) => ja[e];
function Na(e, t) {
	if (t) {
		if (Z.escapeTest.test(e)) return e.replace(Z.escapeReplace, Ma);
	} else if (Z.escapeTestNoEncode.test(e)) return e.replace(Z.escapeReplaceNoEncode, Ma);
	return e;
}
function Pa(e) {
	try {
		e = encodeURI(e).replace(Z.percentDecode, "%");
	} catch {
		return null;
	}
	return e;
}
function Fa(e, t) {
	let n = e.replace(Z.findPipe, (e, t, n) => {
		let r = !1, i = t;
		for (; --i >= 0 && n[i] === "\\";) r = !r;
		return r ? "|" : " |";
	}).split(Z.splitPipe), r = 0;
	if (n[0].trim() || n.shift(), n.length > 0 && !n.at(-1)?.trim() && n.pop(), t) {
		if (n.length > t) n.splice(t);
		else for (; n.length < t;) n.push("");
	}
	for (; r < n.length; r++) n[r] = n[r].trim().replace(Z.slashPipe, "|");
	return n;
}
function Ia(e, t, n) {
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
function La(e) {
	let t = e.split("\n"), n = t.length - 1;
	for (; n >= 0 && Z.blankLine.test(t[n]);) n--;
	return t.length - n <= 2 ? e : t.slice(0, n + 1).join("\n");
}
function Ra(e, t) {
	if (e.indexOf(t[1]) === -1) return -1;
	let n = 0;
	for (let r = 0; r < e.length; r++) if (e[r] === "\\") r++;
	else if (e[r] === t[0]) n++;
	else if (e[r] === t[1] && (n--, n < 0)) return r;
	return n > 0 ? -2 : -1;
}
function za(e, t = 0) {
	let n = t, r = "";
	for (let t of e) if (t === "	") {
		let e = 4 - n % 4;
		r += " ".repeat(e), n += e;
	} else r += t, n++;
	return r;
}
function Ba(e, t, n, r, i) {
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
function Va(e, t, n) {
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
var Ha = class {
	options;
	rules;
	lexer;
	constructor(e) {
		this.options = e || hi;
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
			let e = this.options.pedantic ? t[0] : La(t[0]);
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
			let e = t[0], n = Va(e, t[3] || "", this.rules);
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
				let t = Ia(e, "#");
				(this.options.pedantic || !t || this.rules.other.endingSpaceChar.test(t)) && (e = t.trim());
			}
			return {
				type: "heading",
				raw: Ia(t[0], "\n"),
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
			raw: Ia(t[0], "\n")
		};
	}
	blockquote(e) {
		let t = this.rules.block.blockquote.exec(e);
		if (t) {
			let e = Ia(t[0], "\n").split("\n"), n = "", r = "", i = [];
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
				let c = za(t[2].split("\n", 1)[0], t[1].length), l = e.split("\n", 1)[0], u = !c.trim(), d = 0;
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
			let e = La(t[0]);
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
				raw: Ia(t[0], "\n"),
				href: n,
				title: r
			};
		}
	}
	table(e) {
		let t = this.rules.block.table.exec(e);
		if (!t || !this.rules.other.tableDelimiter.test(t[2])) return;
		let n = Fa(t[1]), r = t[2].replace(this.rules.other.tableAlignChars, "").split("|"), i = t[3]?.trim() ? t[3].replace(this.rules.other.tableRowBlankLine, "").split("\n") : [], a = {
			type: "table",
			raw: Ia(t[0], "\n"),
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
			for (let e of i) a.rows.push(Fa(e, a.header.length).map((e, t) => ({
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
				raw: Ia(t[0], "\n"),
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
				let t = Ia(e.slice(0, -1), "\\");
				if ((e.length - t.length) % 2 == 0) return;
			} else {
				let e = Ra(t[2], "()");
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
			return n = n.trim(), this.rules.other.startAngleBracket.test(n) && (n = this.options.pedantic && !this.rules.other.endAngleBracket.test(e) ? n.slice(1) : n.slice(1, -1)), Ba(t, {
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
			return Ba(n, e, n[0], this.lexer, this.rules);
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
}, Ua = class e {
	tokens;
	options;
	state;
	inlineQueue;
	tokenizer;
	constructor(e) {
		this.tokens = [], this.tokens.links = Object.create(null), this.options = e || hi, this.options.tokenizer = this.options.tokenizer || new Ha(), this.tokenizer = this.options.tokenizer, this.tokenizer.options = this.options, this.tokenizer.lexer = this, this.inlineQueue = [], this.state = {
			inLink: !1,
			inRawBlock: !1,
			top: !0
		};
		let t = {
			other: Z,
			block: ka.normal,
			inline: Aa.normal
		};
		this.options.pedantic ? (t.block = ka.pedantic, t.inline = Aa.pedantic) : this.options.gfm && (t.block = ka.gfm, t.inline = this.options.breaks ? Aa.breaks : Aa.gfm), this.tokenizer.rules = t;
	}
	static get rules() {
		return {
			block: ka,
			inline: Aa
		};
	}
	static lex(t, n) {
		return new e(n).lex(t);
	}
	static lexInline(t, n) {
		return new e(n).inlineTokens(t);
	}
	lex(e) {
		e = e.replace(Z.carriageReturn, "\n"), this.blockTokens(e, this.tokens);
		for (let e = 0; e < this.inlineQueue.length; e++) {
			let t = this.inlineQueue[e];
			this.inlineTokens(t.src, t.tokens);
		}
		return this.inlineQueue = [], this.tokens;
	}
	blockTokens(e, t = [], n = !1) {
		this.tokenizer.lexer = this, this.options.pedantic && (e = e.replace(Z.tabCharGlobal, "    ").replace(Z.spaceLine, ""));
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
}, Wa = class {
	options;
	parser;
	constructor(e) {
		this.options = e || hi;
	}
	space(e) {
		return "";
	}
	code({ text: e, lang: t, escaped: n }) {
		let r = (t || "").match(Z.notSpaceStart)?.[0], i = e.replace(Z.endingNewline, "") + "\n";
		return r ? "<pre><code class=\"language-" + Na(r) + "\">" + (n ? i : Na(i, !0)) + "</code></pre>\n" : "<pre><code>" + (n ? i : Na(i, !0)) + "</code></pre>\n";
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
		return `<code>${Na(e, !0)}</code>`;
	}
	br(e) {
		return "<br>";
	}
	del({ tokens: e }) {
		return `<del>${this.parser.parseInline(e)}</del>`;
	}
	link({ href: e, title: t, tokens: n }) {
		let r = this.parser.parseInline(n), i = Pa(e);
		if (i === null) return r;
		e = i;
		let a = "<a href=\"" + e + "\"";
		return t && (a += " title=\"" + Na(t) + "\""), a += ">" + r + "</a>", a;
	}
	image({ href: e, title: t, text: n, tokens: r }) {
		r && (n = this.parser.parseInline(r, this.parser.textRenderer));
		let i = Pa(e);
		if (i === null) return Na(n);
		e = i;
		let a = `<img src="${e}" alt="${Na(n)}"`;
		return t && (a += ` title="${Na(t)}"`), a += ">", a;
	}
	text(e) {
		return "tokens" in e && e.tokens ? this.parser.parseInline(e.tokens) : "escaped" in e && e.escaped ? e.text : Na(e.text);
	}
}, Ga = class {
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
}, Ka = class e {
	options;
	renderer;
	textRenderer;
	constructor(e) {
		this.options = e || hi, this.options.renderer = this.options.renderer || new Wa(), this.renderer = this.options.renderer, this.renderer.options = this.options, this.renderer.parser = this, this.textRenderer = new Ga();
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
}, qa = class {
	options;
	block;
	constructor(e) {
		this.options = e || hi;
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
		return e ? Ua.lex : Ua.lexInline;
	}
	provideParser(e = this.block) {
		return e ? Ka.parse : Ka.parseInline;
	}
}, Ja = class {
	defaults = mi();
	options = this.setOptions;
	parse = this.parseMarkdown(!0);
	parseInline = this.parseMarkdown(!1);
	Parser = Ka;
	Renderer = Wa;
	TextRenderer = Ga;
	Lexer = Ua;
	Tokenizer = Ha;
	Hooks = qa;
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
				let t = this.defaults.renderer || new Wa(this.defaults);
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
				let t = this.defaults.tokenizer || new Ha(this.defaults);
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
				let t = this.defaults.hooks || new qa();
				for (let n in e.hooks) {
					if (!(n in t)) throw Error(`hook '${n}' does not exist`);
					if (["options", "block"].includes(n)) continue;
					let r = n, i = e.hooks[r], a = t[r];
					t[r] = qa.passThroughHooks.has(n) ? (e) => {
						if (this.defaults.async && qa.passThroughHooksRespectAsync.has(n)) return (async () => {
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
		return Ua.lex(e, t ?? this.defaults);
	}
	parser(e, t) {
		return Ka.parse(e, t ?? this.defaults);
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
				let n = i.hooks ? await i.hooks.preprocess(t) : t, r = await (i.hooks ? await i.hooks.provideLexer(e) : e ? Ua.lex : Ua.lexInline)(n, i), a = i.hooks ? await i.hooks.processAllTokens(r) : r;
				i.walkTokens && await Promise.all(this.walkTokens(a, i.walkTokens));
				let o = await (i.hooks ? await i.hooks.provideParser(e) : e ? Ka.parse : Ka.parseInline)(a, i);
				return i.hooks ? await i.hooks.postprocess(o) : o;
			})().catch(a);
			try {
				i.hooks && (t = i.hooks.preprocess(t));
				let n = (i.hooks ? i.hooks.provideLexer(e) : e ? Ua.lex : Ua.lexInline)(t, i);
				i.hooks && (n = i.hooks.processAllTokens(n)), i.walkTokens && this.walkTokens(n, i.walkTokens);
				let r = (i.hooks ? i.hooks.provideParser(e) : e ? Ka.parse : Ka.parseInline)(n, i);
				return i.hooks && (r = i.hooks.postprocess(r)), r;
			} catch (e) {
				return a(e);
			}
		};
	}
	onError(e, t) {
		return (n) => {
			if (n.message += "\nPlease report this to https://github.com/markedjs/marked.", e) {
				let e = "<p>An error occurred:</p><pre>" + Na(n.message + "", !0) + "</pre>";
				return t ? Promise.resolve(e) : e;
			}
			if (t) return Promise.reject(n);
			throw n;
		};
	}
}, Ya = new Ja();
function Q(e, t) {
	return Ya.parse(e, t);
}
Q.options = Q.setOptions = function(e) {
	return Ya.setOptions(e), Q.defaults = Ya.defaults, gi(Q.defaults), Q;
}, Q.getDefaults = mi, Q.defaults = hi;
function Xa(...e) {
	return Ya.use(...e), Q.defaults = Ya.defaults, gi(Q.defaults), Q;
}
Q.use = Xa, Q.walkTokens = function(e, t) {
	return Ya.walkTokens(e, t);
}, Q.parseInline = Ya.parseInline, Q.Parser = Ka, Q.parser = Ka.parse, Q.Renderer = Wa, Q.TextRenderer = Ga, Q.Lexer = Ua, Q.lexer = Ua.lex, Q.Tokenizer = Ha, Q.Hooks = qa, Q.parse = Q, Q.options, Q.setOptions, Q.walkTokens, Q.parseInline, Ka.parse, Ua.lex;
//#endregion
//#region src/presentation.ts
var Za = {
	imageUnavailable: "Image unavailable",
	imageUnavailableDetails: "Image preview released from local memory; Agent history is unchanged.",
	imageError: (e) => ({
		count: "A message allows at most four images.",
		budget: "Images exceed the remaining 8 MiB base64 budget.",
		type: "Image signature and MIME must match PNG, JPEG, WebP or GIF.",
		dimensions: "Images must fit 8,000 pixels per edge and 16 million pixels total.",
		decode: "The image could not be read or decoded."
	})[e],
	composerAdd: "Add to message",
	addImages: "Images",
	imagesUnsupported: "This Agent does not accept images. Your draft is unchanged.",
	removeImage: (e) => `Remove image: ${e}`,
	imageBudget: (e, t) => `${(e / 1048576).toFixed(2)} MiB used · ${(t / 1048576).toFixed(2)} MiB remaining`,
	recoverDraft: "Append undelivered draft",
	back: "Back",
	accept: "Continue",
	addContext: "Add context",
	agentName: (e) => e ? `${Qa(e)} Agent` : "Agent",
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
	mode: "Mode",
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
	sessionPhase: (e) => Qa(e),
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
	usage: (e, t) => `${$a(e)} / ${$a(t)}`,
	you: "You",
	confirmDeleteSession: (e) => `Delete “${e}”?`,
	backToSession: (e) => `Back to ${e}`
};
function Qa(e) {
	return e.replaceAll(/[_-]+/g, " ").trim().replaceAll(/(^|\s)\S/g, (e) => e.toUpperCase());
}
function $a(e) {
	return e < 0xe8d4a51000 ? e.toLocaleString() : e.toExponential(2);
}
//#endregion
//#region src/react/clipboard.ts
var eo = 1e3;
function to(e) {
	let [t, n] = F(!1), r = L(!1), i = L(void 0), a = L(0);
	return I(() => (a.current += 1, r.current = !1, n(!1), i.current !== void 0 && (window.clearTimeout(i.current), i.current = void 0), () => {
		a.current += 1, r.current = !1, i.current !== void 0 && (window.clearTimeout(i.current), i.current = void 0);
	}), [e]), {
		copied: t,
		copy: R((o) => {
			if (!e || t || r.current) return;
			let s = a.current;
			r.current = !0, no(e, o).then((e) => {
				s === a.current && (r.current = !1, e && (n(!0), i.current = window.setTimeout(() => {
					i.current = void 0, n(!1);
				}, eo)));
			});
		}, [t, e])
	};
}
async function no(e, t) {
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
//#region src/react/MessageActions.tsx
var ro = new Intl.DateTimeFormat(void 0, {
	month: "short",
	day: "numeric"
}), io = new Intl.DateTimeFormat(void 0, {
	year: "numeric",
	month: "short",
	day: "numeric"
});
function ao({ content: e, timestamp: t, clock: n, labels: r }) {
	let i = fo(), { copied: a, copy: o } = to(so(e)), s = t !== void 0 && Number.isFinite(t) && t >= 0 && !Number.isNaN(new Date(t).valueOf()) ? t : void 0, c = s === void 0 ? null : /* @__PURE__ */ H("time", {
		className: `paui-message__time paui-message__time--${n}`,
		dateTime: new Date(s).toISOString(),
		children: oo(s, i)
	}), l = a ? r.copied : r.copy;
	return /* @__PURE__ */ H("div", {
		className: "paui-message__actions",
		"data-pretty-aui-slot": "message-actions",
		"data-clock": n,
		children: [
			n === "start" ? c : null,
			/* @__PURE__ */ H("button", {
				className: "paui-message__action",
				type: "button",
				"aria-label": l,
				title: l,
				onClick: (e) => o(e.currentTarget),
				children: H(a ? bo : yo, {})
			}),
			n === "end" ? c : null
		]
	});
}
function oo(e, t = Date.now()) {
	let n = new Date(e), r = new Date(t), i = `${_o(n.getHours())}:${_o(n.getMinutes())}`, a = n.getFullYear() === r.getFullYear();
	return a && n.getMonth() === r.getMonth() && n.getDate() === r.getDate() ? i : `${a ? ro.format(n) : io.format(n)} ${i}`;
}
function so(e) {
	return e.flatMap((e) => e.type === "text" && typeof e.text == "string" ? [e.text] : []).join("");
}
var co = ho(Date.now()), lo, uo = /* @__PURE__ */ new Set();
function fo() {
	return pt(po, () => co, () => co);
}
function po(e) {
	uo.add(e);
	let t = ho(Date.now());
	if (t !== co) {
		co = t;
		for (let e of uo) e();
	}
	return uo.size === 1 && mo(), () => {
		uo.delete(e), !uo.size && lo !== void 0 && (window.clearTimeout(lo), lo = void 0);
	};
}
function mo() {
	lo !== void 0 && window.clearTimeout(lo);
	let e = Date.now();
	lo = window.setTimeout(() => {
		lo = void 0, co = ho(Date.now());
		for (let e of uo) e();
		uo.size && mo();
	}, go(e));
}
function ho(e) {
	let t = new Date(e);
	return t.setHours(0, 0, 0, 0), t.getTime();
}
function go(e) {
	let t = new Date(e);
	return t.setHours(24, 0, 0, 0), Math.max(1, t.getTime() - e);
}
function _o(e) {
	return String(e).padStart(2, "0");
}
function vo({ children: e }) {
	return /* @__PURE__ */ H("svg", {
		viewBox: "0 0 16 16",
		"aria-hidden": "true",
		focusable: "false",
		children: e
	});
}
function yo() {
	return /* @__PURE__ */ H(vo, { children: [/* @__PURE__ */ H("rect", {
		x: "2.5",
		y: "4.5",
		width: "9",
		height: "9",
		rx: "2"
	}), /* @__PURE__ */ H("path", { d: "M5 4V3.5a2 2 0 0 1 2-2h5.5a2 2 0 0 1 2 2V9a2 2 0 0 1-2 2H12" })] });
}
function bo() {
	return /* @__PURE__ */ H(vo, { children: /* @__PURE__ */ H("path", { d: "m3 8.25 3.15 3.15L13 4.55" }) });
}
//#endregion
//#region src/react/tool-block-model.ts
var xo = 1e5;
function So(e) {
	return Eo(e) ?? wo(e) ?? To(e) ?? Do(e);
}
function Co(e) {
	return (typeof e == "string" ? e : (() => {
		try {
			return JSON.stringify(e, null, 2) ?? String(e);
		} catch {
			return String(e);
		}
	})()).slice(0, xo);
}
function wo(e) {
	let t = e.kind?.toLowerCase();
	if (t !== "execute" && t !== "bash" && t !== "shell" && t !== "terminal" || !Wo(e.rawInput)) return;
	let n = Ho(e.rawInput.command, e.rawInput.cmd);
	if (!n?.trim()) return;
	let r = Ho(e.rawInput.cwd, e.rawInput.workdir), { text: i, remaining: a } = ko(e.content), o = Wo(e.rawOutput) ? e.rawOutput : void 0, s = i ?? Ho(o?.output, o?.error) ?? (typeof e.rawOutput == "string" ? e.rawOutput : ""), c = e.status === "pending" || e.status === "in_progress";
	return {
		kind: "terminal",
		command: n,
		...r ? { cwd: r } : {},
		output: s,
		displayOutput: Uo(s),
		running: c,
		failed: e.status === "failed" || e.status === "cancelled",
		supplementary: a
	};
}
function To(e) {
	if (e.kind?.toLowerCase() !== "read" || e.status !== "completed") return;
	let t = Wo(e.rawInput) ? e.rawInput : void 0, n = Wo(e.rawOutput) ? e.rawOutput : void 0, r = Wo(n?.metadata) ? n.metadata : void 0, i = Wo(r?.display) ? r.display : void 0;
	if (i?.type === "directory") return;
	let { text: a, remaining: o } = ko(e.content), s = i?.type === "file" && typeof i.text == "string" ? i.text : void 0, c = a ?? s;
	if (c === void 0) return;
	let l = i?.type === "file", u = Fo(c), d = Io(u?.text ?? c);
	if (!l && !u && !d) return;
	let f = u?.text ?? c, p = Vo(t?.offset) ?? 1, m = d ?? Lo(f).map((e, t) => ({
		number: p + t,
		text: e
	})), h = Ho(u?.path, t?.filePath, t?.file_path, t?.filepath, t?.path, Bo(e)), g = zo(e.title) ?? h;
	if (g) return {
		kind: "read",
		label: g,
		lines: m,
		copyText: m.map((e) => e.text).join("\n"),
		supplementary: o
	};
}
function Eo(e) {
	let t = [], n = [], r = /* @__PURE__ */ new Set(), i = /* @__PURE__ */ new Set(), a = 0, o = 0;
	if (e.content.forEach((e, s) => {
		if (!Wo(e) || e.type !== "diff") return;
		let c = Mo(e);
		if (c) {
			r.add(s), i.add(c.path);
			let e = [{
				kind: "meta",
				text: c.path
			}];
			if (c.oldText !== null) for (let t of Ro(c.oldText)) e.push({
				kind: "delete",
				text: `- ${t}`
			}), o += 1;
			for (let t of Ro(c.newText)) e.push({
				kind: "add",
				text: `+ ${t}`
			}), a += 1;
			t.push(...e), n.push(e.map((e) => e.text).join("\n"));
			return;
		}
		let l = No(e);
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
function Do(e) {
	let t = e.rawInput === void 0 ? void 0 : Oo(Co(e.rawInput));
	if (e.content.length) {
		let n = Ao(e.content);
		return {
			kind: "io",
			...t ? { input: t } : {},
			output: {
				values: e.content,
				copyText: n
			}
		};
	}
	let n = e.rawOutput === void 0 ? void 0 : Oo(Co(e.rawOutput));
	return {
		kind: "io",
		...t ? { input: t } : {},
		...n ? { output: n } : {}
	};
}
function Oo(e) {
	return {
		text: e,
		copyText: e
	};
}
function ko(e) {
	let t = [], n = [];
	for (let r of e) {
		let e = jo(r);
		e === void 0 ? n.push(r) : t.push(e);
	}
	return {
		...t.length ? { text: t.join("\n") } : {},
		remaining: n
	};
}
function Ao(e) {
	return e.flatMap((e) => {
		let t = jo(e);
		return t === void 0 ? [] : [t];
	}).join("\n");
}
function jo(e) {
	if (!(!Wo(e) || e.type !== "content" || !Wo(e.content))) return e.content.type === "text" && typeof e.content.text == "string" ? e.content.text : void 0;
}
function Mo(e) {
	if (!(typeof e.path != "string" || !e.path.trim() || typeof e.newText != "string") && (e.oldText === void 0 || e.oldText === null || typeof e.oldText == "string")) return {
		path: e.path,
		oldText: typeof e.oldText == "string" ? e.oldText : null,
		newText: e.newText
	};
}
function No(e) {
	if (!Array.isArray(e.changes)) return;
	let t = e.changes.filter(Wo);
	if (t.length !== e.changes.length) return;
	let n = [];
	for (let e of t) {
		if (typeof e.operation != "string" || !e.operation.trim() || typeof e.path != "string" || !e.path.trim()) return;
		n.push(e.path), typeof e.oldPath == "string" && n.push(e.oldPath);
	}
	let r = typeof e.patch == "string" ? e.patch : Wo(e.patch) && typeof e.patch.text == "string" ? e.patch.text : void 0;
	if (r !== void 0) return {
		rows: r.split(/\r?\n/).map(Po),
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
function Po(e) {
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
function Fo(e) {
	let t = /^<path>([^\r\n]*)<\/path>\r?\n<type>file<\/type>\r?\n<content>\r?\n([\s\S]*)\r?\n<\/content>$/.exec(e);
	return t?.[1] !== void 0 && t[2] !== void 0 ? {
		path: t[1],
		text: t[2]
	} : void 0;
}
function Io(e) {
	let t = Lo(e);
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
function Lo(e) {
	return e ? (e.endsWith("\n") ? e.slice(0, -1) : e).split(/\r?\n/) : [];
}
function Ro(e) {
	return e ? Lo(e) : [];
}
function zo(e) {
	let t = e.trim(), n = t.toLowerCase();
	return t && n !== "read" && n !== "tool" ? t : void 0;
}
function Bo(e) {
	return e.locations.find((e) => typeof e.path == "string")?.path;
}
function Vo(e) {
	return typeof e == "number" && Number.isSafeInteger(e) && e > 0 ? e : void 0;
}
function Ho(...e) {
	return e.find((e) => typeof e == "string");
}
function Uo(e) {
	return e.replaceAll(/\u001b\][^\u0007\u001b]*(?:\u0007|\u001b\\)?/g, "").replaceAll(/\u001b\[[\u0030-\u003f]*[\u0020-\u002f]*[\u0040-\u007e]/g, "").replaceAll("\r\n", "\n").replaceAll("\r", "\n").replaceAll(/[\u0000-\u0008\u000b\u000c\u000e-\u001a\u001c-\u001f\u007f]/g, "");
}
function Wo(e) {
	return typeof e == "object" && !!e && !Array.isArray(e);
}
//#endregion
//#region src/react/ToolBlocks.tsx
function Go({ tool: e, labels: t, renderContent: n }) {
	let r = So(e);
	switch (r.kind) {
		case "terminal": return /* @__PURE__ */ H(j, { children: [/* @__PURE__ */ H(Ko, {
			model: r,
			status: e.status,
			labels: t
		}), /* @__PURE__ */ H(Qo, {
			values: r.supplementary,
			render: n
		})] });
		case "read": return /* @__PURE__ */ H(j, { children: [/* @__PURE__ */ H(qo, {
			model: r,
			labels: t
		}), /* @__PURE__ */ H(Qo, {
			values: r.supplementary,
			render: n
		})] });
		case "diff": return /* @__PURE__ */ H(j, { children: [/* @__PURE__ */ H(Yo, {
			model: r,
			labels: t
		}), /* @__PURE__ */ H(Qo, {
			values: r.supplementary,
			render: n
		})] });
		case "io": return !r.input && !r.output ? /* @__PURE__ */ H("span", {
			className: "paui-muted",
			children: t.tool
		}) : /* @__PURE__ */ H("div", {
			className: "paui-tool-block paui-tool-io",
			"data-tool-block": "io",
			children: [
				r.input ? /* @__PURE__ */ H(Zo, {
					label: t.toolInput,
					section: r.input,
					labels: t,
					render: n
				}) : null,
				r.input && r.output ? /* @__PURE__ */ H("span", {
					className: "paui-tool-io__divider",
					"aria-hidden": "true"
				}) : null,
				r.output ? /* @__PURE__ */ H(Zo, {
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
function Ko({ model: e, status: t, labels: n }) {
	let r = e.displayOutput.trim().length > 0;
	return /* @__PURE__ */ H("div", {
		className: "paui-tool-block paui-tool-terminal",
		"data-tool-block": "terminal",
		"data-state": e.failed ? "failed" : e.running ? "running" : "completed",
		children: [/* @__PURE__ */ H("div", {
			className: "paui-tool-terminal__header",
			children: [/* @__PURE__ */ H("div", {
				className: "paui-tool-terminal__prompt",
				children: [/* @__PURE__ */ H("span", {
					className: "paui-sr-only",
					children: t
				}), ns(e.command).map((t, n) => /* @__PURE__ */ H("div", {
					className: "paui-tool-terminal__prompt-line",
					children: [
						n === 0 ? /* @__PURE__ */ H("span", {
							className: "paui-tool-terminal__state",
							"aria-hidden": "true"
						}) : null,
						/* @__PURE__ */ H("span", {
							className: "paui-tool-terminal__cwd",
							children: n === 0 && e.cwd ? e.cwd : "$"
						}),
						/* @__PURE__ */ H("span", {
							className: "paui-tool-terminal__command",
							children: t
						})
					]
				}, n))]
			}), !e.running && r ? /* @__PURE__ */ H($o, {
				text: e.output,
				labels: n
			}) : null]
		}), e.running ? null : r ? /* @__PURE__ */ H("pre", {
			className: "paui-tool-terminal__output",
			children: e.displayOutput
		}) : /* @__PURE__ */ H("div", {
			className: "paui-tool-block__empty",
			children: n.toolNoOutput
		})]
	});
}
function qo({ model: e, labels: t }) {
	let [n, r] = F(!1), i = ts(e.lines, n);
	return /* @__PURE__ */ H("div", {
		className: "paui-tool-block paui-tool-read",
		"data-tool-block": "read",
		children: [/* @__PURE__ */ H("div", {
			className: "paui-tool-block__banner",
			children: [/* @__PURE__ */ H("span", {
				className: "paui-tool-block__label",
				children: e.label
			}), e.copyText ? /* @__PURE__ */ H($o, {
				text: e.copyText,
				labels: t
			}) : null]
		}), /* @__PURE__ */ H("div", {
			className: "paui-tool-read__body",
			children: [
				/* @__PURE__ */ H(Jo, { lines: i.head }),
				i.hidden > 0 ? /* @__PURE__ */ H(es, {
					expanded: n,
					hidden: i.hidden,
					labels: t,
					onClick: () => r((e) => !e)
				}) : null,
				/* @__PURE__ */ H(Jo, { lines: i.tail })
			]
		})]
	});
}
function Jo({ lines: e }) {
	return e.map((e) => /* @__PURE__ */ H("div", {
		className: "paui-tool-read__line",
		children: [/* @__PURE__ */ H("span", {
			className: "paui-tool-read__gutter",
			"aria-hidden": "true",
			children: e.number
		}), /* @__PURE__ */ H("span", {
			className: "paui-tool-read__content",
			children: e.text
		})]
	}, e.number));
}
function Yo({ model: e, labels: t }) {
	let [n, r] = F(!1), i = ts(e.rows, n);
	return /* @__PURE__ */ H("div", {
		className: "paui-tool-block paui-tool-diff",
		"data-tool-block": "diff",
		children: [
			/* @__PURE__ */ H("div", {
				className: "paui-tool-block__banner paui-tool-diff__banner",
				children: [/* @__PURE__ */ H("span", {
					className: "paui-tool-block__label",
					children: t.changedFiles
				}), /* @__PURE__ */ H($o, {
					text: e.copyText,
					labels: t
				})]
			}),
			/* @__PURE__ */ H("div", {
				className: "paui-tool-diff__body",
				children: [
					/* @__PURE__ */ H(Xo, { rows: i.head }),
					i.hidden > 0 ? /* @__PURE__ */ H(es, {
						expanded: n,
						hidden: i.hidden,
						labels: t,
						onClick: () => r((e) => !e)
					}) : null,
					/* @__PURE__ */ H(Xo, { rows: i.tail })
				]
			}),
			/* @__PURE__ */ H("div", {
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
function Xo({ rows: e }) {
	return e.map((e, t) => /* @__PURE__ */ H("div", {
		className: "paui-tool-diff__line",
		"data-line-kind": e.kind,
		children: e.text
	}, t));
}
function Zo({ label: e, section: t, labels: n, render: r, failed: i = !1 }) {
	return /* @__PURE__ */ H("section", {
		className: "paui-tool-io__section",
		"data-error": i || void 0,
		children: [/* @__PURE__ */ H("div", {
			className: "paui-tool-io__section-header",
			children: [/* @__PURE__ */ H("strong", { children: e }), t.copyText ? /* @__PURE__ */ H($o, {
				text: t.copyText,
				labels: n
			}) : null]
		}), /* @__PURE__ */ H("div", {
			className: "paui-tool-io__content",
			children: [t.text === void 0 ? null : /* @__PURE__ */ H("pre", { children: t.text }), t.values?.map(r)]
		})]
	});
}
function Qo({ values: e, render: t }) {
	return e.length ? /* @__PURE__ */ H("div", {
		className: "paui-tool-supplementary",
		children: e.map(t)
	}) : null;
}
function $o({ text: e, labels: t }) {
	let { copied: n, copy: r } = to(e), i = n ? t.copied : t.copy;
	return /* @__PURE__ */ H("button", {
		className: "paui-tool-block__copy",
		type: "button",
		"aria-label": i,
		title: i,
		onClick: (e) => r(e.currentTarget),
		children: i
	});
}
function es({ expanded: e, hidden: t, labels: n, onClick: r }) {
	return /* @__PURE__ */ H("button", {
		className: "paui-tool-block__fold",
		type: "button",
		"aria-expanded": e,
		onClick: r,
		children: e ? n.toolCollapseLines : n.toolExpandLines(t)
	});
}
function ts(e, t) {
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
function ns(e) {
	return (e.endsWith("\n") ? e.slice(0, -1) : e).split("\n");
}
//#endregion
//#region src/react/Chat.tsx
var rs = Ve(void 0), is = /* @__PURE__ */ new WeakMap(), as = 0, os = {
	draft: Vt,
	promptCapabilities: {
		image: !1,
		audio: !1,
		embeddedContext: !1
	},
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
}, ss = {
	setDraft() {},
	appendDraft() {},
	addDraftImages() {},
	removeDraftImage() {},
	selectCommand() {},
	recoverDraft() {},
	getComposerActions: () => [],
	async runComposerAction() {
		return !1;
	},
	sendDraft() {
		throw Error("The chat session is still connecting");
	},
	ready: new Promise(() => void 0),
	getSnapshot: () => os,
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
function cs(e) {
	let t = rt(rs);
	if (!t) throw Error(`pretty-aui: ${e} must be rendered inside a ChatRoot.`);
	return t;
}
function ls(e) {
	return /* @__PURE__ */ H(us, {
		...e,
		children: [
			/* @__PURE__ */ H(ps, {}),
			/* @__PURE__ */ H(ms, {}),
			/* @__PURE__ */ H(hs, {}),
			/* @__PURE__ */ H(Ws, {})
		]
	});
}
function us(e) {
	if ("controller" in e) {
		let { controller: t, ...n } = e;
		return /* @__PURE__ */ H(fs, {
			...n,
			controller: t
		}, lc(t));
	}
	let { options: t, ...n } = e;
	return /* @__PURE__ */ H(ds, {
		...n,
		options: t
	});
}
function ds(e) {
	let { options: t, ...n } = e, r = L(t), [i, a] = F();
	return I(() => {
		let e = _n(r.current);
		return a(e), () => {
			e.destroy();
		};
	}, []), i ? /* @__PURE__ */ H(fs, {
		...n,
		controller: i
	}, lc(i)) : /* @__PURE__ */ H(fs, {
		...n,
		controller: ss
	}, "connecting");
}
function fs(e) {
	let { controller: t } = e, n = pt(R((e) => dc(t, e), [t]), R(() => t.getSnapshot(), [t]), R(() => t.getSnapshot(), [t])), r = nt(() => ({
		...Za,
		...e.labels
	}), [e.labels]), i = z().replaceAll(":", ""), [a, o] = F(), s = R((e) => {
		o(void 0), e().catch((e) => {
			o(e instanceof Error ? e.message : String(e));
		});
	}, []), c = e.colorScheme ?? "system", l = e.surface ?? "inline", u = nt(() => ({
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
	return /* @__PURE__ */ H("section", {
		className: ["pretty-aui", e.className].filter(Boolean).join(" "),
		"data-pretty-aui-slot": "root",
		"data-surface": l,
		"data-scheme": c,
		"data-phase": n.phase,
		style: e.style,
		"aria-label": n.agentName ?? r.assistantName,
		children: /* @__PURE__ */ H(rs.Provider, {
			value: u,
			children: e.children
		})
	});
}
function ps() {
	let { controller: e, snapshot: t, labels: n, runAction: r } = cs("ChatHeader"), [i, a] = F(!1), o = t.sessionTitle ?? n.sessionUntitled, s = t.sessionTrail.at(-1), c = t.protocolVersion !== void 0 && t.phase !== "connecting" && t.phase !== "auth_required" && t.phase !== "closed" && t.loadedSessions.length < 16;
	return /* @__PURE__ */ H(j, { children: [/* @__PURE__ */ H("header", {
		className: "paui-header",
		"data-pretty-aui-slot": "header",
		children: [/* @__PURE__ */ H("div", {
			className: `paui-identity${s ? " paui-identity--child" : ""}`,
			children: [/* @__PURE__ */ H("span", {
				className: "paui-presence",
				"data-phase": t.phase,
				"aria-hidden": "true"
			}), s ? /* @__PURE__ */ H("div", {
				className: "paui-lineage",
				"data-depth": t.sessionTrail.length,
				children: [
					/* @__PURE__ */ H("button", {
						className: "paui-lineage__back",
						type: "button",
						disabled: t.phase !== "idle",
						"aria-label": n.backToSession(s.title ?? s.sessionId),
						onClick: () => r(() => e.openAncestorSession(s.sessionId)),
						children: /* @__PURE__ */ H(Tc, {})
					}),
					/* @__PURE__ */ H("div", {
						className: "paui-lineage__titles",
						children: [t.sessionTrail.map((n) => {
							let i = n.title ?? n.sessionId;
							return /* @__PURE__ */ H("span", {
								className: "paui-lineage__ancestor",
								children: [/* @__PURE__ */ H("button", {
									type: "button",
									disabled: t.phase !== "idle",
									onClick: () => r(() => e.openAncestorSession(n.sessionId)),
									children: i
								}), /* @__PURE__ */ H("span", {
									"aria-hidden": "true",
									children: "/"
								})]
							}, n.sessionId);
						}), /* @__PURE__ */ H("strong", { children: o })]
					}),
					/* @__PURE__ */ H("span", {
						className: "paui-protocol",
						children: t.protocolVersion ? `ACP v${t.protocolVersion}` : t.phase
					})
				]
			}) : /* @__PURE__ */ H("div", { children: [/* @__PURE__ */ H("strong", { children: o }), /* @__PURE__ */ H("span", {
				className: "paui-protocol",
				children: t.protocolVersion ? `ACP v${t.protocolVersion}` : t.phase
			})] })]
		}), /* @__PURE__ */ H("div", {
			className: "paui-header__actions",
			children: [
				t.usage ? /* @__PURE__ */ H("span", {
					className: "paui-usage",
					children: n.usage(t.usage.used, t.usage.size)
				}) : null,
				t.capabilities.listSessions || t.loadedSessions.length > 1 ? /* @__PURE__ */ H("button", {
					className: "paui-icon-button",
					type: "button",
					onClick: () => a(!0),
					children: [/* @__PURE__ */ H(_c, {}), /* @__PURE__ */ H("span", {
						className: "paui-sr-only",
						children: n.sessions
					})]
				}) : null,
				/* @__PURE__ */ H("button", {
					className: "paui-icon-button",
					type: "button",
					disabled: !c,
					onClick: () => r(() => e.newSession()),
					children: [/* @__PURE__ */ H(vc, {}), /* @__PURE__ */ H("span", {
						className: "paui-sr-only",
						children: n.newChat
					})]
				})
			]
		})]
	}), i ? /* @__PURE__ */ H($s, {
		controller: e,
		snapshot: t,
		labels: n,
		onClose: () => a(!1)
	}) : null] });
}
function ms() {
	let { snapshot: e, labels: t, toolActivityRenderer: n } = cs("ChatTranscript"), r = L(null), i = L(null), a = L(!0), o = L(0), s = uc(e), c = L(s), l = L(/* @__PURE__ */ new Map()), [u, d] = F(!0), f = R((e = "auto") => {
		let t = r.current;
		t && (typeof t.scrollTo == "function" ? t.scrollTo({
			top: t.scrollHeight,
			behavior: e
		}) : t.scrollTop = t.scrollHeight, o.current = t.scrollTop, a.current = !0, d(!0));
	}, []), p = R(() => {
		let e = r.current;
		if (!e) return;
		let t = e.scrollHeight - e.scrollTop - e.clientHeight, n = e.scrollTop < o.current - 1, i = t <= 24 || !n && a.current;
		o.current = e.scrollTop, a.current = i, l.current.set(s, {
			top: e.scrollTop,
			pinned: i
		}), d(i);
	}, [s]);
	tt(() => {
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
	}, [f, s]), tt(() => {
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
	let m = nt(() => _s(e.activities), [e.activities]), h = e.phase === "running" || e.phase === "awaiting_user" || e.phase === "cancelling", g = h ? gs(m) : -1, _ = nt(() => js(e.activities, h), [e.activities, h]);
	return /* @__PURE__ */ H(j, { children: [/* @__PURE__ */ H("main", {
		ref: r,
		className: "paui-body",
		"data-pretty-aui-slot": "transcript",
		tabIndex: 0,
		onScroll: p,
		children: /* @__PURE__ */ H("div", {
			className: "paui-transcript",
			ref: i,
			children: [
				e.historyGap ? /* @__PURE__ */ H("aside", {
					className: "paui-notice",
					role: "status",
					children: [/* @__PURE__ */ H(Vc, {}), /* @__PURE__ */ H("div", { children: [/* @__PURE__ */ H("strong", { children: t.historyGapTitle }), /* @__PURE__ */ H("span", { children: t.historyGap })] })]
				}) : null,
				e.activities.length ? null : /* @__PURE__ */ H("div", {
					className: "paui-empty",
					children: [
						/* @__PURE__ */ H(Uc, {}),
						/* @__PURE__ */ H("strong", { children: t.emptyTitle }),
						/* @__PURE__ */ H("p", { children: t.emptyDescription })
					]
				}),
				m.map((e, r) => e.kind === "notice" ? /* @__PURE__ */ H(vs, {
					group: e,
					labels: t
				}, e.id) : /* @__PURE__ */ H(ys, {
					group: e,
					labels: t,
					toolActivityRenderer: n,
					active: r === g,
					completedAnswerIds: _
				}, e.id))
			]
		})
	}), u ? null : /* @__PURE__ */ H("div", {
		className: "paui-to-bottom-row",
		children: /* @__PURE__ */ H("button", {
			className: "paui-to-bottom",
			type: "button",
			onClick: () => f("smooth"),
			"aria-label": t.scrollToLatest,
			children: /* @__PURE__ */ H(wc, {})
		})
	})] });
}
function hs() {
	let { controller: e, snapshot: t, labels: n, actionError: r, runAction: i } = cs("ChatInteractions"), a = L(null);
	return I(() => {
		if (!t.interactions.length) return;
		let e = a.current;
		if (!e) return;
		let n = tc(e);
		n && e.contains(n) || e.querySelector(rc)?.focus();
	}, [t.interactions.map((e) => e.id).join("\0"), t.interactions.length]), /* @__PURE__ */ H("div", {
		ref: a,
		className: "paui-interactions",
		"data-pretty-aui-slot": "interactions",
		children: [
			t.phase === "auth_required" ? /* @__PURE__ */ H(Qs, {}) : null,
			t.interactions.map((t) => t.type === "permission" ? /* @__PURE__ */ H(Js, {
				interaction: t,
				controller: e,
				labels: n
			}, t.id) : /* @__PURE__ */ H(Ys, {
				interaction: t,
				controller: e,
				labels: n
			}, t.id)),
			t.error ? /* @__PURE__ */ H("aside", {
				className: "paui-error",
				role: "alert",
				children: [/* @__PURE__ */ H("div", { children: [/* @__PURE__ */ H("strong", { children: n.error }), /* @__PURE__ */ H("span", { children: t.error.message })] }), t.error.retryable ? /* @__PURE__ */ H("button", {
					type: "button",
					onClick: () => i(() => e.reconnect()),
					children: n.retry
				}) : null]
			}) : null,
			r && !t.error ? /* @__PURE__ */ H("aside", {
				className: "paui-error",
				role: "alert",
				children: /* @__PURE__ */ H("div", { children: [/* @__PURE__ */ H("strong", { children: n.error }), /* @__PURE__ */ H("span", { children: r })] })
			}) : null
		]
	});
}
function gs(e) {
	for (let t = e.length - 1; t >= 0; --t) if (e[t]?.kind === "turn") return t;
	return -1;
}
function _s(e) {
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
function vs({ group: e, labels: t }) {
	return /* @__PURE__ */ H("div", {
		className: "paui-notice-group",
		children: e.activities.map((e) => /* @__PURE__ */ H(bs, {
			activity: e,
			labels: t,
			running: !1,
			showMessageActions: !1
		}, e.id))
	});
}
function ys({ group: e, labels: t, toolActivityRenderer: n, active: r, completedAnswerIds: i }) {
	return /* @__PURE__ */ H("article", {
		className: "paui-turn",
		children: [e.user ? /* @__PURE__ */ H(As, {
			message: e.user,
			labels: t,
			showActions: !0
		}) : null, e.activities.length ? /* @__PURE__ */ H("div", {
			className: "paui-activities",
			children: e.activities.map((a, o) => /* @__PURE__ */ H(bs, {
				activity: a,
				labels: t,
				toolActivityRenderer: n,
				running: r && o === e.activities.length - 1,
				showMessageActions: i.has(a.id)
			}, a.id))
		}) : null]
	});
}
var bs = gt(function({ activity: e, labels: t, toolActivityRenderer: n, running: r, showMessageActions: i }) {
	return /* @__PURE__ */ H("div", {
		className: "paui-activity",
		"data-pretty-aui-slot": "activity",
		"data-kind": e.type === "message" ? e.role : e.type === "tool" && e.subagent ? "subagent" : e.type,
		"data-level": e.type === "notice" ? e.level : void 0,
		"data-status": pc(e),
		children: /* @__PURE__ */ H(xs, {
			activity: e,
			labels: t,
			toolActivityRenderer: n,
			running: r,
			showMessageActions: i
		})
	});
});
function xs({ activity: e, labels: t, toolActivityRenderer: n, running: r, showMessageActions: i }) {
	switch (e.type) {
		case "message": return /* @__PURE__ */ H(As, {
			message: e,
			labels: t,
			running: r,
			showActions: i
		});
		case "context": return /* @__PURE__ */ H(Ss, {
			activity: e,
			labels: t
		});
		case "notice": return /* @__PURE__ */ H("div", {
			className: "paui-host-notice",
			role: e.level === "error" ? "alert" : "status",
			children: [/* @__PURE__ */ H("span", {
				className: "paui-host-notice__icon",
				"aria-hidden": "true",
				children: e.level === "error" ? /* @__PURE__ */ H(Hc, {}) : /* @__PURE__ */ H(Vc, {})
			}), /* @__PURE__ */ H("span", { children: e.text })]
		});
		case "tool": return e.subagent ? /* @__PURE__ */ H(Es, {
			tool: e,
			labels: t,
			renderer: n
		}) : /* @__PURE__ */ H("details", {
			className: "paui-disclosure paui-tool",
			"data-state": e.status,
			children: [/* @__PURE__ */ H("summary", {
				className: "paui-flow-summary",
				children: [
					/* @__PURE__ */ H(Ns, { icon: /* @__PURE__ */ H(Ls, { kind: e.kind }) }),
					/* @__PURE__ */ H("span", {
						className: "paui-flow-title",
						children: Is(e.kind, t.tool)
					}),
					/* @__PURE__ */ H("span", {
						className: "paui-flow-separator",
						"aria-hidden": "true"
					}),
					/* @__PURE__ */ H("span", {
						className: "paui-flow-preview",
						children: e.title
					}),
					/* @__PURE__ */ H("span", {
						className: "paui-sr-only",
						children: e.status
					})
				]
			}), /* @__PURE__ */ H("div", {
				className: "paui-disclosure__body",
				children: /* @__PURE__ */ H(Rs, {
					tool: e,
					labels: t,
					renderer: n
				})
			})]
		});
		case "plan": return /* @__PURE__ */ H("details", {
			className: "paui-disclosure paui-plan",
			open: !0,
			children: [/* @__PURE__ */ H("summary", { children: [
				/* @__PURE__ */ H(jc, {}),
				/* @__PURE__ */ H("span", { children: t.plan }),
				/* @__PURE__ */ H(gc, { status: fc(e.entries) })
			] }), /* @__PURE__ */ H("ol", {
				className: "paui-plan__list",
				children: e.entries.map((e, t) => /* @__PURE__ */ H("li", {
					"data-status": e.status,
					children: [/* @__PURE__ */ H("span", {
						className: "paui-plan__mark",
						"aria-hidden": "true"
					}), /* @__PURE__ */ H("span", { children: e.content })]
				}, `${e.content}-${t}`))
			})]
		});
		case "terminal": return /* @__PURE__ */ H("details", {
			className: "paui-disclosure paui-terminal",
			children: [/* @__PURE__ */ H("summary", { children: [
				/* @__PURE__ */ H(Fc, {}),
				/* @__PURE__ */ H("span", { children: e.title }),
				/* @__PURE__ */ H(gc, { status: e.exited ? "completed" : "in_progress" })
			] }), /* @__PURE__ */ H("pre", { children: e.output })]
		});
		case "unsupported": return /* @__PURE__ */ H("div", {
			className: "paui-unsupported",
			children: t.unsupportedContent(e.kind)
		});
	}
}
function Ss({ activity: e, labels: t }) {
	return /* @__PURE__ */ H("details", {
		className: "paui-disclosure paui-context-injection",
		children: [/* @__PURE__ */ H("summary", {
			className: "paui-flow-summary",
			children: [
				/* @__PURE__ */ H(Ns, { icon: /* @__PURE__ */ H(Bc, {}) }),
				/* @__PURE__ */ H("span", {
					className: "paui-flow-title",
					children: t.contextInjection
				}),
				/* @__PURE__ */ H("span", {
					className: "paui-flow-separator",
					"aria-hidden": "true"
				}),
				/* @__PURE__ */ H("span", {
					className: "paui-flow-preview",
					children: e.label
				})
			]
		}), /* @__PURE__ */ H("div", {
			className: "paui-context-injection__body",
			tabIndex: 0,
			children: e.content.map((n, r) => /* @__PURE__ */ H(Cs, {
				block: n,
				labels: t
			}, `${e.id}:${r}`))
		})]
	});
}
function Cs({ block: e, labels: t }) {
	if (e.type === "text" && typeof e.text == "string") return /* @__PURE__ */ H(ws, {
		text: e.text,
		labels: t
	});
	if (e.type === "resource" && hc(e.resource)) {
		let n = e.resource;
		return /* @__PURE__ */ H("section", {
			className: "paui-context-block",
			children: [/* @__PURE__ */ H("div", {
				className: "paui-context-meta",
				children: [/* @__PURE__ */ H("span", { children: String(n.uri ?? t.resource) }), typeof n.mimeType == "string" ? /* @__PURE__ */ H("span", { children: n.mimeType }) : null]
			}), typeof n.text == "string" ? /* @__PURE__ */ H(ws, {
				text: n.text,
				labels: t
			}) : typeof n.blob == "string" ? /* @__PURE__ */ H("span", {
				className: "paui-muted",
				children: `Binary resource · ${n.blob.length.toLocaleString()} base64 characters`
			}) : null]
		});
	}
	if (e.type === "resource_link" && typeof e.uri == "string") {
		let n = typeof e.title == "string" ? e.title : typeof e.name == "string" ? e.name : t.resource, r = typeof e.mimeType == "string" ? e.mimeType : void 0, i = typeof e.description == "string" ? e.description : void 0;
		return /* @__PURE__ */ H("section", {
			className: "paui-context-block",
			children: [
				/* @__PURE__ */ H("div", {
					className: "paui-context-meta",
					children: [/* @__PURE__ */ H("span", { children: n }), r ? /* @__PURE__ */ H("span", { children: r }) : null]
				}),
				/* @__PURE__ */ H("span", {
					className: "paui-context-identifier",
					children: e.uri
				}),
				i ? /* @__PURE__ */ H("span", { children: i }) : null
			]
		});
	}
	return (e.type === "image" || e.type === "audio") && typeof e.mimeType == "string" && typeof e.data == "string" ? /* @__PURE__ */ H("span", {
		className: "paui-context-meta",
		children: `${Is(e.type, e.type)} · ${e.mimeType} · ${e.data.length.toLocaleString()} base64 characters`
	}) : /* @__PURE__ */ H(ws, {
		text: Co(e),
		labels: t
	});
}
function ws({ text: e, labels: t }) {
	let n = Ts(e);
	return /* @__PURE__ */ H(j, { children: [/* @__PURE__ */ H("pre", {
		className: "paui-context-text",
		children: n.text
	}), n.truncated ? /* @__PURE__ */ H("span", {
		className: "paui-context-truncated",
		children: t.contextTruncated(e.length)
	}) : null] });
}
function Ts(e) {
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
function Es({ tool: e, labels: t, renderer: n }) {
	let { controller: r, snapshot: i, runAction: a } = cs("ChatTranscript"), o = e.subagent, s = e.status === "pending" || e.status === "in_progress", c = Ds(e.id, s), l = ks(e, t), u = i.capabilities.loadSession || i.capabilities.resumeSession;
	return /* @__PURE__ */ H("div", {
		className: "paui-subagent-row",
		children: [/* @__PURE__ */ H("details", {
			className: "paui-disclosure paui-subagent",
			"data-state": e.status,
			"data-running": s || void 0,
			children: [/* @__PURE__ */ H("summary", {
				className: "paui-flow-summary",
				children: [
					/* @__PURE__ */ H(Ns, { icon: /* @__PURE__ */ H(kc, {}) }),
					/* @__PURE__ */ H("span", {
						className: "paui-flow-title",
						children: t.agentName(o.agent)
					}),
					o.description ? /* @__PURE__ */ H(j, { children: [/* @__PURE__ */ H("span", {
						className: "paui-flow-separator",
						"aria-hidden": "true"
					}), /* @__PURE__ */ H("span", {
						className: "paui-flow-preview",
						children: o.description
					})] }) : null,
					/* @__PURE__ */ H("span", {
						className: "paui-subagent-status",
						"data-status": e.status,
						children: [s ? /* @__PURE__ */ H("span", {
							className: "paui-subagent-status__ongoing",
							children: [/* @__PURE__ */ H("span", {
								className: "paui-subagent-status__spinner",
								"aria-hidden": "true"
							}), /* @__PURE__ */ H("span", { children: t.agentOngoing })]
						}) : /* @__PURE__ */ H("span", { children: l }), c ? /* @__PURE__ */ H("span", { children: t.agentObserved(c) }) : null]
					})
				]
			}), /* @__PURE__ */ H("div", {
				className: "paui-disclosure__body",
				children: /* @__PURE__ */ H(Rs, {
					tool: e,
					labels: t,
					renderer: n
				})
			})]
		}), o.sessionId ? /* @__PURE__ */ H("button", {
			className: "paui-subagent-open",
			type: "button",
			disabled: !u || i.phase !== "idle",
			"aria-label": t.openChildSession,
			onClick: () => a(() => r.openChildSession(o.sessionId)),
			children: /* @__PURE__ */ H(Ac, {})
		}) : null]
	});
}
function Ds(e, t) {
	let n = L(Date.now()), [r, i] = F(n.current);
	return I(() => {
		n.current = Date.now(), i(n.current);
	}, [e]), I(() => {
		if (!t) return;
		let e = window.setInterval(() => i(Date.now()), 1e3);
		return () => window.clearInterval(e);
	}, [t]), t ? Os(r - n.current) : void 0;
}
function Os(e) {
	let t = Math.max(0, Math.floor(e / 1e3));
	if (t < 60) return `${t}s`;
	let n = Math.floor(t / 60), r = t % 60;
	return n < 60 ? `${n}m ${String(r).padStart(2, "0")}s` : `${Math.floor(n / 60)}h ${String(n % 60).padStart(2, "0")}m`;
}
function ks(e, t) {
	return e.subagent?.background && e.status === "completed" ? t.agentBackground : e.status === "completed" ? t.agentCompleted : e.status === "failed" ? t.agentFailed : e.status === "cancelled" ? t.agentCancelled : Is(e.status, t.agentCompleted);
}
function As({ message: e, labels: t, running: n = !1, showActions: r = !1 }) {
	return e.role === "thought" ? /* @__PURE__ */ H(Ms, {
		message: e,
		labels: t,
		running: n
	}) : /* @__PURE__ */ H("div", {
		className: "paui-message",
		"data-pretty-aui-slot": "message",
		"data-role": e.role,
		"data-pending": e.pending || void 0,
		"data-time-hover-root": r || void 0,
		"aria-live": e.role === "assistant" && n ? "polite" : void 0,
		"aria-atomic": e.role === "assistant" && n ? "false" : void 0,
		children: [/* @__PURE__ */ H("div", {
			className: "paui-message__bubble",
			children: [/* @__PURE__ */ H("span", {
				className: "paui-message__label",
				children: e.role === "user" ? t.you : t.assistantName
			}), /* @__PURE__ */ H("div", {
				className: "paui-message__content",
				children: e.content.map((e, n) => /* @__PURE__ */ H(Hs, {
					block: e,
					labels: t
				}, n))
			})]
		}), r ? /* @__PURE__ */ H(ao, {
			content: e.content,
			timestamp: e.timestamp,
			clock: e.role === "user" ? "start" : "end",
			labels: t
		}) : null]
	});
}
function js(e, t) {
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
function Ms({ message: e, labels: t, running: n }) {
	let r = L(null), i = Ps(e.content, n);
	return tt(() => {
		let e = r.current;
		e && (e.scrollLeft = n ? e.scrollWidth - e.clientWidth : 0);
	}, [i, n]), /* @__PURE__ */ H("details", {
		className: "paui-thought",
		"data-running": n || void 0,
		children: [/* @__PURE__ */ H("summary", {
			className: "paui-flow-summary",
			children: [
				/* @__PURE__ */ H(Ns, { icon: /* @__PURE__ */ H(Mc, {}) }),
				/* @__PURE__ */ H("span", {
					className: "paui-flow-title",
					children: t.thinking
				}),
				i ? /* @__PURE__ */ H(j, { children: [/* @__PURE__ */ H("span", {
					className: "paui-flow-separator",
					"aria-hidden": "true"
				}), /* @__PURE__ */ H("span", {
					ref: r,
					className: "paui-flow-preview",
					"data-follow-end": n || void 0,
					children: i
				})] }) : null
			]
		}), /* @__PURE__ */ H("div", {
			className: "paui-thought__body",
			children: e.content.map((e, n) => /* @__PURE__ */ H(Hs, {
				block: e,
				labels: t
			}, n))
		})]
	});
}
function Ns({ icon: e }) {
	return /* @__PURE__ */ H("span", {
		className: "paui-flow-leading",
		"aria-hidden": "true",
		children: [/* @__PURE__ */ H("span", {
			className: "paui-flow-icon",
			children: e
		}), /* @__PURE__ */ H("span", {
			className: "paui-flow-chevron",
			children: /* @__PURE__ */ H(Ec, {})
		})]
	});
}
function Ps(e, t) {
	if (t) {
		for (let t = e.length - 1; t >= 0; --t) {
			let n = Fs(e[t]).trimEnd();
			if (n) return n.slice(n.lastIndexOf("\n") + 1).replace(/\r$/, "").trim();
		}
		return "";
	}
	let n = e.map(Fs).filter(Boolean).join("\n").trimEnd();
	return n ? n.split(/\r?\n/)[0]?.trim() ?? "" : "";
}
function Fs(e) {
	return e.type === "text" && typeof e.text == "string" ? e.text : e.type === "resource" && hc(e.resource) && typeof e.resource.text == "string" ? e.resource.text : "";
}
function Is(e, t) {
	if (!e) return t;
	let n = e.replaceAll(/[_-]+/g, " ").trim();
	return n ? `${n[0].toUpperCase()}${n.slice(1)}` : t;
}
function Ls({ kind: e }) {
	let t = e?.toLowerCase() ?? "";
	return t.includes("read") || t.includes("browse") || t.includes("context") ? /* @__PURE__ */ H(Nc, {}) : t.includes("search") || t.includes("find") ? /* @__PURE__ */ H(Pc, {}) : t.includes("bash") || t.includes("shell") || t.includes("terminal") || t.includes("execute") ? /* @__PURE__ */ H(Fc, {}) : /* @__PURE__ */ H(Oc, {});
}
function Rs({ tool: e, labels: t, renderer: n }) {
	let r = /* @__PURE__ */ H(zs, {
		tool: e,
		labels: t
	});
	return n ? /* @__PURE__ */ H(Vs, {
		fallback: r,
		resetKey: e.id,
		children: /* @__PURE__ */ H(Bs, {
			tool: e,
			renderer: n,
			fallback: r
		})
	}, e.id) : r;
}
function zs({ tool: e, labels: t }) {
	return /* @__PURE__ */ H(Go, {
		tool: e,
		labels: t,
		renderContent: (e, n) => /* @__PURE__ */ H(Us, {
			value: e,
			labels: t
		}, n)
	});
}
function Bs({ tool: e, renderer: t, fallback: n }) {
	let r = t(e);
	return r === void 0 ? n : r;
}
var Vs = class extends M {
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
function Hs({ block: e, labels: t }) {
	let n = nt(() => e.type === "text" && typeof e.text == "string" ? ac(e.text) : void 0, [e]);
	if (n !== void 0) return /* @__PURE__ */ H("div", {
		className: "paui-markdown",
		dangerouslySetInnerHTML: { __html: n }
	});
	if (e.type === "image_unavailable") return /* @__PURE__ */ H("span", {
		title: t.imageUnavailableDetails,
		children: t.imageUnavailable
	});
	if (e.type === "image" && typeof e.data == "string" && typeof e.mimeType == "string" && e.mimeType.startsWith("image/")) return /* @__PURE__ */ H("img", {
		className: "paui-media",
		src: `data:${e.mimeType};base64,${e.data}`,
		alt: ""
	});
	if (e.type === "audio" && typeof e.data == "string" && typeof e.mimeType == "string" && e.mimeType.startsWith("audio/")) return /* @__PURE__ */ H("audio", {
		className: "paui-media",
		controls: !0,
		src: `data:${e.mimeType};base64,${e.data}`
	});
	if (e.type === "resource_link" && typeof e.uri == "string") {
		let n = typeof e.title == "string" ? e.title : typeof e.name == "string" ? e.name : e.uri;
		return cc(e.uri) ? /* @__PURE__ */ H("a", {
			className: "paui-resource",
			href: e.uri,
			target: "_blank",
			rel: "noreferrer",
			children: [/* @__PURE__ */ H(Lc, {}), /* @__PURE__ */ H("span", { children: n })]
		}) : /* @__PURE__ */ H("span", {
			className: "paui-unsupported",
			children: t.unsupportedContent(t.unsafeResourceLink)
		});
	}
	if (e.type === "resource" && hc(e.resource)) {
		let n = e.resource, r = typeof n.uri == "string" ? n.uri : t.resource;
		return typeof n.text == "string" ? /* @__PURE__ */ H("details", {
			className: "paui-resource",
			children: [/* @__PURE__ */ H("summary", { children: [/* @__PURE__ */ H(Rc, {}), r] }), /* @__PURE__ */ H("pre", { children: n.text })]
		}) : /* @__PURE__ */ H("span", {
			className: "paui-resource",
			children: [/* @__PURE__ */ H(Rc, {}), r]
		});
	}
	return /* @__PURE__ */ H("span", {
		className: "paui-unsupported",
		children: t.unsupportedContent(e.type)
	});
}
function Us({ value: e, labels: t }) {
	if (!hc(e)) return null;
	if (e.type === "content" && hc(e.content) && typeof e.content.type == "string") return /* @__PURE__ */ H(Hs, {
		block: e.content,
		labels: t
	});
	if (e.type === "diff") {
		let n = typeof e.path == "string" ? e.path : t.changedFiles, r = typeof e.patch == "string" ? e.patch : typeof e.newText == "string" ? e.newText : void 0;
		return /* @__PURE__ */ H("details", {
			className: "paui-diff",
			children: [/* @__PURE__ */ H("summary", { children: [/* @__PURE__ */ H(zc, {}), n] }), r ? /* @__PURE__ */ H("pre", { children: r }) : /* @__PURE__ */ H("span", {
				className: "paui-muted",
				children: t.binaryChange
			})]
		});
	}
	return e.type === "terminal" ? /* @__PURE__ */ H("span", {
		className: "paui-muted",
		children: [
			/* @__PURE__ */ H(Fc, {}),
			" ",
			t.terminalOutputInActivity
		]
	}) : /* @__PURE__ */ H("span", {
		className: "paui-unsupported",
		children: t.unsupportedContent(typeof e.type == "string" ? e.type : t.toolResult)
	});
}
function Ws() {
	let { controller: e, snapshot: t, labels: n, runAction: r, ids: i } = cs("ChatComposer"), a = t.draft.text, [o, s] = F(0), [c, l] = F(!1), u = L(!1), d = L(null), f = L(null), p = L(null), m = uc(t), h = L(null), [g, _] = F(!1);
	I(() => {
		_(!0);
	}, []);
	let v = L(0);
	tt(() => (v.current++, () => {
		v.current++;
	}), [m]);
	let y = (i) => r(async () => {
		let r = t.sessionInstanceId, a = v.current;
		if (!t.promptCapabilities.image) throw Error(n.imagesUnsupported);
		let o = await Bn(i, e.getSnapshot().draft.images).catch((e) => {
			throw e instanceof Rn ? Error(n.imageError(e.issue)) : e;
		});
		r === e.getSnapshot().sessionInstanceId && v.current === a && e.addDraftImages(o);
	}), b = t.activities.some((e) => e.type !== "notice") || t.interactions.length || t.phase === "auth_required" || t.error ? "docked" : "hero";
	tt(() => {
		let e = d.current;
		e && (e.style.height = "0px", e.style.height = `${Math.min(e.scrollHeight, 336)}px`);
	}, [b, a]);
	let x = !t.sessionId || t.phase === "connecting" || t.phase === "auth_required" || t.phase === "closed", S = x || t.draft.locked, C = t.phase === "running" || t.phase === "awaiting_user" || t.phase === "cancelling", w = () => {
		!a.trim() && !t.draft.images.length || S || C || (l(!0), r(async () => {
			await e.sendDraft().done;
		}));
	}, T = !t.draft.locked && a.startsWith("/") && !/\s/.test(a.slice(1)) && !c ? t.commands.filter((e) => e.name.startsWith(a.slice(1).split(/\s/, 1)[0] ?? "")) : [], E = Math.min(o, Math.max(0, T.length - 1)), ee = (t) => {
		e.setDraft(`/${t} `), l(!0), d.current?.focus();
	}, D = (e) => {
		if (!e.repeat) {
			if (T.length && e.key === "ArrowDown") {
				e.preventDefault(), s((E + 1) % T.length);
				return;
			}
			if (T.length && e.key === "ArrowUp") {
				e.preventDefault(), s((E - 1 + T.length) % T.length);
				return;
			}
			if (T.length && e.key === "Escape") {
				e.preventDefault(), l(!0);
				return;
			}
			if (T.length && e.key === "Tab" && !e.shiftKey) {
				e.preventDefault();
				let t = T[E];
				t && ee(t.name);
				return;
			}
			if (e.key === "Enter" && !e.shiftKey && !u.current && !e.nativeEvent.isComposing) {
				e.preventDefault();
				let t = T[E];
				t ? ee(t.name) : w();
			}
		}
	}, te = `${i.instance}-commands`;
	return tt(() => {
		let e = p.current, t = f.current, n = e?.closest(".pretty-aui");
		if (!e || !t || !n) return;
		let r = () => {
			let r = t.getBoundingClientRect().top - n.getBoundingClientRect().top - 8;
			e.style.maxHeight = `${Math.max(48, Math.min(320, Math.floor(r)))}px`;
		};
		r();
		let i = globalThis.ResizeObserver ? new ResizeObserver(r) : void 0;
		return i?.observe(n), i?.observe(t), globalThis.addEventListener?.("resize", r), () => {
			i?.disconnect(), globalThis.removeEventListener?.("resize", r);
		};
	}, [
		T.length,
		b,
		t.contextSelection.items.length
	]), tt(() => {
		let e = p.current, t = e?.querySelector(`#${te}-${E}`);
		!e || !t || (t.offsetTop < e.scrollTop ? e.scrollTop = t.offsetTop : t.offsetTop + t.offsetHeight > e.scrollTop + e.clientHeight && (e.scrollTop = t.offsetTop + t.offsetHeight - e.clientHeight));
	}, [
		te,
		T.length,
		E
	]), /* @__PURE__ */ H("footer", {
		className: "paui-composer-wrap",
		"data-pretty-aui-slot": "composer",
		"data-placement": b,
		children: [T.length ? /* @__PURE__ */ H("div", {
			ref: p,
			className: "paui-commands",
			role: "listbox",
			id: te,
			"aria-label": n.commands,
			children: T.map((e, t) => /* @__PURE__ */ H("button", {
				type: "button",
				id: `${te}-${t}`,
				role: "option",
				"aria-selected": t === E,
				onMouseDown: (e) => e.preventDefault(),
				onClick: () => ee(e.name),
				children: [/* @__PURE__ */ H("code", { children: ["/", e.name] }), /* @__PURE__ */ H("span", { children: e.description })]
			}, e.name))
		}) : null, /* @__PURE__ */ H("div", {
			ref: f,
			className: "paui-composer",
			"data-pretty-aui-slot": "composer-input",
			onDragOver: (e) => {
				e.dataTransfer.types.includes("Files") && e.preventDefault();
			},
			onDrop: (e) => {
				e.dataTransfer.files.length && (e.preventDefault(), e.stopPropagation(), S || y(Array.from(e.dataTransfer.files)));
			},
			children: [
				g && /* @__PURE__ */ H("input", {
					ref: h,
					type: "file",
					accept: "image/png,image/jpeg,image/webp,image/gif",
					multiple: !0,
					hidden: !0,
					onChange: (e) => {
						let t = Array.from(e.currentTarget.files ?? []);
						e.currentTarget.value = "", t.length && y(t);
					}
				}),
				t.draft.images.length > 0 && /* @__PURE__ */ H("div", {
					className: "paui-composer-images",
					role: "group",
					"aria-label": n.addImages,
					children: [/* @__PURE__ */ H(Kn, {
						images: t.draft.images,
						sessionInstanceId: t.sessionInstanceId,
						disabled: S,
						remove: (t) => e.removeDraftImage(t),
						labels: n
					}), /* @__PURE__ */ H("small", { children: n.imageBudget(Wt(t.draft.images), 8388608 - Wt(t.draft.images)) })]
				}),
				t.draft.recoverable.map((t, i) => {
					let a = (t.text || t.images.map((e) => e.name).join(", ")).replace(/\s+/g, " ").slice(0, 80);
					return /* @__PURE__ */ H("button", {
						type: "button",
						disabled: S,
						"aria-label": `${n.recoverDraft} ${i + 1}: ${a}`,
						onClick: () => r(async () => e.recoverDraft(t.id)),
						children: [
							n.recoverDraft,
							" ",
							/* @__PURE__ */ H("small", { children: [
								i + 1,
								". ",
								a
							] })
						]
					}, t.id);
				}),
				t.contextSelection.items.length ? /* @__PURE__ */ H("div", {
					className: "paui-composer__context",
					"data-pretty-aui-slot": "composer-context",
					role: "group",
					"aria-label": n.contextSelection,
					children: t.contextSelection.items.map((i) => /* @__PURE__ */ H("span", {
						className: "paui-context-chip",
						"data-pretty-aui-slot": "composer-context-item",
						title: i.label,
						children: [/* @__PURE__ */ H("span", {
							className: "paui-context-chip__label",
							children: i.label
						}), t.contextSelection.canRemove ? /* @__PURE__ */ H("button", {
							type: "button",
							"aria-label": n.removeContext(i.label),
							title: n.removeContext(i.label),
							disabled: S || C || t.contextSelection.busy,
							onMouseDown: (e) => e.preventDefault(),
							onClick: () => r(() => e.removeContext(i.id)),
							children: /* @__PURE__ */ H("span", {
								"aria-hidden": "true",
								children: "×"
							})
						}) : null]
					}, i.id))
				}) : null,
				/* @__PURE__ */ H("textarea", {
					ref: d,
					rows: 1,
					value: a,
					disabled: x,
					readOnly: t.draft.locked,
					"aria-busy": t.draft.locked || void 0,
					onPaste: (e) => {
						if (e.clipboardData.getData("text/plain")) return;
						let t = Array.from(e.clipboardData.files);
						t.length && (e.preventDefault(), S || y(t));
					},
					placeholder: n.composerPlaceholder,
					"aria-label": n.composerPlaceholder,
					role: "combobox",
					"aria-autocomplete": "list",
					"aria-haspopup": "listbox",
					"aria-controls": T.length ? te : void 0,
					"aria-expanded": !!T.length,
					"aria-activedescendant": T.length ? `${te}-${E}` : void 0,
					onInput: (n) => {
						if (t.draft.locked) return;
						let r = n.currentTarget.value;
						e.setDraft(r), s(0), l(!1);
					},
					onCompositionStart: () => {
						u.current = !0;
					},
					onCompositionEnd: () => {
						u.current = !1;
					},
					onKeyDown: D
				}),
				/* @__PURE__ */ H("div", {
					className: "paui-composer__actions",
					"data-pretty-aui-slot": "composer-actions",
					children: [
						/* @__PURE__ */ H(qn, {
							controller: e,
							snapshot: t,
							labels: n,
							disabled: S,
							onImages: () => h.current?.click(),
							runAction: r,
							focusComposer: () => d.current?.focus()
						}),
						t.configOptions.length ? /* @__PURE__ */ H(Gs, {
							controller: e,
							options: t.configOptions
						}) : /* @__PURE__ */ H("span", {}),
						C ? /* @__PURE__ */ H("button", {
							className: "paui-send paui-stop",
							type: "button",
							onMouseDown: (e) => e.preventDefault(),
							onClick: () => r(() => e.cancel()),
							disabled: t.phase === "cancelling",
							children: [/* @__PURE__ */ H(Cc, {}), /* @__PURE__ */ H("span", {
								className: "paui-sr-only",
								children: n.stop
							})]
						}) : /* @__PURE__ */ H("button", {
							className: "paui-send",
							type: "button",
							onMouseDown: (e) => e.preventDefault(),
							onClick: w,
							disabled: S || !a.trim() && !t.draft.images.length,
							children: [/* @__PURE__ */ H(Sc, {}), /* @__PURE__ */ H("span", {
								className: "paui-sr-only",
								children: n.send
							})]
						})
					]
				})
			]
		})]
	});
}
function Gs({ controller: e, options: t }) {
	let { labels: n, runAction: r } = cs("ChatComposer");
	return /* @__PURE__ */ H("div", {
		className: "paui-config",
		children: t.map((t) => {
			let i = qs(t, n);
			return t.type === "boolean" ? /* @__PURE__ */ H("label", {
				title: t.description,
				children: [/* @__PURE__ */ H("input", {
					type: "checkbox",
					checked: !!t.currentValue,
					onChange: (n) => r(() => e.setConfigOption(t.id, n.target.checked))
				}), /* @__PURE__ */ H("span", { children: i })]
			}, t.id) : t.type === "select" ? /* @__PURE__ */ H(Ks, {
				controller: e,
				label: i,
				option: t
			}, t.id) : null;
		})
	});
}
function Ks({ controller: e, label: t, option: n }) {
	let { runAction: r } = cs("ChatComposer"), i = L(null), a = L(null), o = L(null), s = `paui-config-${z().replaceAll(":", "")}`, c = n.options ?? [], l = c.findIndex((e) => e.value === String(n.currentValue)), u = l >= 0 ? c[l] : void 0, [d, f] = F(!1), [p, m] = F(Math.max(0, l)), h = (e = Math.max(0, l)) => {
		c.length && (m(e), f(!0));
	}, g = (e = !1) => {
		f(!1), e && a.current?.focus();
	}, _ = (t) => {
		let i = c[t];
		i && (g(!0), i.value !== String(n.currentValue) && r(() => e.setConfigOption(n.id, i.value)));
	}, v = (e) => {
		c.length && m((t) => (t + e + c.length) % c.length);
	};
	return I(() => {
		if (!d) return;
		let e = (e) => {
			i.current && e.composedPath().includes(i.current) || f(!1);
		};
		return window.addEventListener("pointerdown", e, !0), () => window.removeEventListener("pointerdown", e, !0);
	}, [d]), I(() => {
		d && (o.current?.querySelector(`#${s}-option-${p}`))?.scrollIntoView?.({ block: "nearest" });
	}, [
		p,
		s,
		d
	]), /* @__PURE__ */ H("div", {
		className: "paui-config__field",
		ref: i,
		children: [/* @__PURE__ */ H("button", {
			ref: a,
			className: "paui-config__trigger",
			type: "button",
			role: "combobox",
			"aria-label": t,
			"aria-controls": d ? s : void 0,
			"aria-expanded": d,
			"aria-haspopup": "listbox",
			"aria-activedescendant": d ? `${s}-option-${p}` : void 0,
			title: n.description,
			disabled: !c.length,
			onClick: () => d ? g() : h(),
			onKeyDown: (e) => {
				if (e.key === "ArrowDown" || e.key === "ArrowUp") {
					e.preventDefault();
					let t = e.key === "ArrowDown" ? 1 : -1;
					d ? v(t) : h(((l >= 0 ? l : 0) + t + c.length) % c.length);
					return;
				}
				if (e.key === "Home" && d) {
					e.preventDefault(), m(0);
					return;
				}
				if (e.key === "End" && d) {
					e.preventDefault(), m(Math.max(0, c.length - 1));
					return;
				}
				if (e.key === "Enter" || e.key === " ") {
					e.preventDefault(), d ? _(p) : h();
					return;
				}
				if (e.key === "Escape" && d) {
					e.preventDefault(), g(!0);
					return;
				}
				e.key === "Tab" && g();
			},
			children: [/* @__PURE__ */ H("span", { children: u?.name ?? String(n.currentValue) }), /* @__PURE__ */ H(Ec, {})]
		}), d ? /* @__PURE__ */ H("div", {
			ref: o,
			className: "paui-config__listbox",
			id: s,
			role: "listbox",
			"aria-label": t,
			children: c.map((e, t) => /* @__PURE__ */ H("button", {
				id: `${s}-option-${t}`,
				className: "paui-config__option",
				type: "button",
				role: "option",
				"aria-selected": e.value === String(n.currentValue),
				"data-active": t === p || void 0,
				title: e.description,
				tabIndex: -1,
				onMouseMove: t === p ? void 0 : () => m(t),
				onMouseDown: (e) => e.preventDefault(),
				onClick: () => _(t),
				children: [/* @__PURE__ */ H("span", { children: e.name }), /* @__PURE__ */ H("span", {
					className: "paui-config__check",
					"aria-hidden": "true",
					children: e.value === String(n.currentValue) ? /* @__PURE__ */ H(Dc, {}) : null
				})]
			}, e.value))
		}) : null]
	});
}
function qs(e, t) {
	return e.category === "mode" || e.id === "mode" ? t.mode : e.name;
}
function Js({ interaction: e, controller: t, labels: n }) {
	let { ids: r } = cs("ChatInteractions"), i = `${r.instance}-${e.id}-title`;
	return /* @__PURE__ */ H("section", {
		className: "paui-interaction",
		role: "alertdialog",
		"aria-labelledby": i,
		children: [/* @__PURE__ */ H("div", {
			className: "paui-interaction__icon",
			children: /* @__PURE__ */ H(Ic, {})
		}), /* @__PURE__ */ H("div", {
			className: "paui-interaction__content",
			children: [
				/* @__PURE__ */ H("strong", {
					id: i,
					children: e.title || n.permission
				}),
				e.description ? /* @__PURE__ */ H("p", { children: e.description }) : null,
				/* @__PURE__ */ H("div", {
					className: "paui-interaction__actions",
					children: [e.options.map((n, r) => /* @__PURE__ */ H("button", {
						type: "button",
						className: n.kind.startsWith("reject") ? "paui-button-secondary" : r === 0 ? "paui-button-primary" : "paui-button-secondary",
						onClick: () => t.respondPermission(e.id, {
							outcome: "selected",
							optionId: n.id
						}),
						children: n.name
					}, n.id)), /* @__PURE__ */ H("button", {
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
function Ys({ interaction: e, controller: t, labels: n }) {
	let { ids: r } = cs("ChatInteractions"), i = `${r.instance}-${e.id}-title`;
	if (e.mode === "url" && e.url) {
		let r = cc(e.url);
		return /* @__PURE__ */ H("section", {
			className: "paui-interaction",
			role: "dialog",
			"aria-labelledby": i,
			children: [/* @__PURE__ */ H("div", {
				className: "paui-interaction__icon",
				children: /* @__PURE__ */ H(Lc, {})
			}), /* @__PURE__ */ H("div", {
				className: "paui-interaction__content",
				children: [
					/* @__PURE__ */ H("strong", {
						id: i,
						children: e.message
					}),
					/* @__PURE__ */ H("code", {
						className: "paui-url",
						children: e.url
					}),
					/* @__PURE__ */ H("div", {
						className: "paui-interaction__actions",
						children: [
							/* @__PURE__ */ H("button", {
								className: "paui-button-primary",
								type: "button",
								disabled: !r,
								onClick: () => r ? window.open(e.url, "_blank", "noopener,noreferrer") : void 0,
								children: n.openLink
							}),
							/* @__PURE__ */ H("button", {
								className: "paui-button-secondary",
								type: "button",
								onClick: () => t.respondElicitation(e.id, { action: "accept" }),
								children: n.finish
							}),
							/* @__PURE__ */ H("button", {
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
	return /* @__PURE__ */ H(Xs, {
		interaction: e,
		controller: t,
		labels: n,
		titleId: i
	});
}
function Xs({ interaction: e, controller: t, labels: n, titleId: r }) {
	let i = e.requestedSchema, a = hc(i?.properties) ? i.properties : {}, o = Array.isArray(i?.required) ? i.required.filter((e) => typeof e == "string") : [];
	return /* @__PURE__ */ H("form", {
		className: "paui-interaction paui-form",
		onSubmit: (n) => {
			n.preventDefault();
			let r = n.currentTarget, i = new FormData(r), o = {};
			for (let [e, t] of Object.entries(a)) if (hc(t)) {
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
		children: [/* @__PURE__ */ H("div", {
			className: "paui-interaction__icon",
			children: /* @__PURE__ */ H(Wc, {})
		}), /* @__PURE__ */ H("div", {
			className: "paui-interaction__content",
			children: [
				/* @__PURE__ */ H("strong", {
					id: r,
					children: e.message
				}),
				/* @__PURE__ */ H("div", {
					className: "paui-fields",
					children: Object.entries(a).map(([e, t]) => hc(t) ? /* @__PURE__ */ H(Zs, {
						name: e,
						schema: t,
						required: o.includes(e)
					}, e) : null)
				}),
				/* @__PURE__ */ H("div", {
					className: "paui-interaction__actions",
					children: [/* @__PURE__ */ H("button", {
						className: "paui-button-primary",
						type: "submit",
						children: n.accept
					}), /* @__PURE__ */ H("button", {
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
function Zs({ name: e, schema: t, required: n }) {
	let r = typeof t.title == "string" ? t.title : e, i = typeof t.description == "string" ? t.description : void 0, a = Array.isArray(t.enum) ? t.enum.filter((e) => typeof e == "string") : [];
	return t.type === "boolean" ? /* @__PURE__ */ H("label", {
		className: "paui-field paui-field--check",
		children: [/* @__PURE__ */ H("input", {
			name: e,
			type: "checkbox"
		}), /* @__PURE__ */ H("span", { children: r })]
	}) : a.length ? /* @__PURE__ */ H("label", {
		className: "paui-field",
		children: [
			/* @__PURE__ */ H("span", { children: r }),
			/* @__PURE__ */ H("select", {
				name: e,
				required: n,
				children: a.map((e) => /* @__PURE__ */ H("option", { children: e }, e))
			}),
			i ? /* @__PURE__ */ H("small", { children: i }) : null
		]
	}) : /* @__PURE__ */ H("label", {
		className: "paui-field",
		children: [
			/* @__PURE__ */ H("span", { children: r }),
			/* @__PURE__ */ H("input", {
				name: e,
				required: n,
				type: t.type === "number" || t.type === "integer" ? "number" : "text"
			}),
			i ? /* @__PURE__ */ H("small", { children: i }) : null
		]
	});
}
function Qs() {
	let { controller: e, snapshot: t, labels: n, runAction: r } = cs("ChatInteractions");
	return /* @__PURE__ */ H("section", {
		className: "paui-auth",
		children: [
			/* @__PURE__ */ H(Ic, {}),
			/* @__PURE__ */ H("strong", { children: n.authRequired }),
			/* @__PURE__ */ H("div", { children: t.authMethods.map((t) => /* @__PURE__ */ H("button", {
				type: "button",
				onClick: () => r(() => e.authenticate(t.id)),
				children: t.name
			}, t.id)) })
		]
	});
}
function $s({ controller: e, snapshot: t, labels: n, onClose: r }) {
	let { ids: i } = cs("ChatHeader"), a = L(null), o = L(null), s = L(null), c = L(null), l = L(null), [u, d] = F(!1), [f, p] = F(), [m, h] = F(), [g, _] = F(), v = ec(t), y = v.find((e) => e.sessionId === m), b = Date.now(), x = u || y?.loaded?.phase === "running" || y?.loaded?.phase === "cancelling" || (y?.loaded?.interactionCount ?? 0) > 0, S = R((e = !1) => {
		let t = l.current;
		h(void 0), _(void 0), e && t?.isConnected && t.focus();
	}, []);
	I(() => {
		let e = tc(o.current), t = e instanceof HTMLElement ? e : void 0;
		return a.current?.focus(), () => {
			t?.isConnected && t.focus();
		};
	}, []), I(() => {
		t.capabilities.listSessions && !t.sessions && (d(!0), e.listSessions().catch((e) => p(e instanceof Error ? e.message : String(e))).finally(() => d(!1)));
	}, [
		e,
		t.capabilities.listSessions,
		t.sessions
	]), tt(() => {
		if (!m) return;
		let e = o.current, t = s.current, n = l.current;
		if (!e || !t || !n) return;
		let r = e.getBoundingClientRect(), i = t.getBoundingClientRect(), a = n.getBoundingClientRect(), c = Math.max(8, r.width - i.width - 8), u = Math.min(Math.max(a.right - r.left - i.width, 8), c), d = a.bottom - r.top + 4, f = a.top - r.top - i.height - 4, p = d + i.height <= r.height - 8 ? d : f, h = Math.max(8, r.height - i.height - 8);
		_({
			left: u,
			top: Math.min(Math.max(p, 8), h)
		});
	}, [m]), tt(() => {
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
			let t = o.current ? [...o.current.querySelectorAll(rc)].filter((e) => !e.hasAttribute("disabled")) : [], n = t[0], i = t.at(-1);
			if (!n || !i) return;
			let a = tc(o.current);
			e.shiftKey && a === n ? (e.preventDefault(), i.focus()) : (!e.shiftKey && a === i || !a || !o.current?.contains(a)) && (e.preventDefault(), n.focus());
		};
		return window.addEventListener("keydown", e, !0), () => window.removeEventListener("keydown", e, !0);
	}, [
		S,
		m,
		r
	]);
	let C = async (t) => {
		d(!0), p(void 0);
		try {
			await e.openSession(t), r();
		} catch (e) {
			p(e instanceof Error ? e.message : String(e));
		} finally {
			d(!1);
		}
	}, w = async (t) => {
		d(!0), p(void 0);
		try {
			await e.listSessions(t);
		} catch (e) {
			p(e instanceof Error ? e.message : String(e));
		} finally {
			d(!1);
		}
	}, T = async (t) => {
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
	return /* @__PURE__ */ H("div", {
		className: "paui-drawer-backdrop",
		role: "presentation",
		onMouseDown: (e) => {
			e.target === e.currentTarget && r();
		},
		children: /* @__PURE__ */ H("aside", {
			ref: o,
			className: "paui-drawer",
			role: "dialog",
			"aria-modal": "true",
			"aria-labelledby": i.sessionsTitle,
			children: [
				/* @__PURE__ */ H("header", { children: [/* @__PURE__ */ H("strong", {
					id: i.sessionsTitle,
					children: n.sessions
				}), /* @__PURE__ */ H("button", {
					ref: a,
					className: "paui-icon-button",
					type: "button",
					onClick: r,
					children: [/* @__PURE__ */ H(yc, {}), /* @__PURE__ */ H("span", {
						className: "paui-sr-only",
						children: n.close
					})]
				})] }),
				/* @__PURE__ */ H("div", {
					className: "paui-session-list",
					children: [
						u && !t.sessions ? /* @__PURE__ */ H("span", {
							className: "paui-muted",
							children: "…"
						}) : null,
						!u && !v.length ? /* @__PURE__ */ H("span", {
							className: "paui-muted",
							children: n.noSessions
						}) : null,
						v.map((e) => {
							let r = e.sessionId === t.sessionId, a = e.title ?? n.sessionUntitled, o = t.capabilities.deleteSession && !r, s = e.sessionId === m;
							return /* @__PURE__ */ H("div", {
								className: "paui-session",
								"data-active": r || void 0,
								"data-has-actions": o || void 0,
								"data-loaded": e.loaded !== void 0 || void 0,
								"data-menu-open": s || void 0,
								children: [/* @__PURE__ */ H("button", {
									className: "paui-session__select",
									type: "button",
									"aria-current": r ? "page" : void 0,
									disabled: u || r,
									onClick: () => void C(e.sessionId),
									children: [e.loaded?.phase === "running" ? /* @__PURE__ */ H("span", {
										className: "paui-session__spinner",
										"aria-hidden": "true"
									}) : null, /* @__PURE__ */ H("strong", {
										className: "paui-session__title",
										children: a
									})]
								}), /* @__PURE__ */ H("span", {
									className: "paui-session__trailing",
									children: [/* @__PURE__ */ H("span", {
										className: "paui-session__meta",
										children: [/* @__PURE__ */ H("span", { children: e.loaded ? n.sessionPhase(e.loaded.phase) : mc(e.updatedAt, b, n.sessionAge) }), e.loaded?.interactionCount ? /* @__PURE__ */ H(j, { children: [/* @__PURE__ */ H("span", {
											className: "paui-session__meta-separator",
											"aria-hidden": "true",
											children: "·"
										}), /* @__PURE__ */ H("span", { children: n.pendingInteractions(e.loaded.interactionCount) })] }) : null]
									}), o ? /* @__PURE__ */ H("button", {
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
										children: /* @__PURE__ */ H(bc, {})
									}) : null]
								})]
							}, e.sessionId);
						}),
						t.sessions?.nextCursor ? /* @__PURE__ */ H("button", {
							className: "paui-load-more",
							type: "button",
							disabled: u,
							onClick: () => void w(t.sessions?.nextCursor),
							children: n.loadMore
						}) : null,
						f ? /* @__PURE__ */ H("span", {
							className: "paui-error-text",
							role: "alert",
							children: f
						}) : null
					]
				}),
				y && t.capabilities.deleteSession && y.sessionId !== t.sessionId ? /* @__PURE__ */ H("div", {
					ref: s,
					id: `${i.instance}-session-menu`,
					className: "paui-session-menu",
					role: "menu",
					"aria-label": n.sessionActions(y.title ?? n.sessionUntitled),
					style: g ?? { visibility: "hidden" },
					children: /* @__PURE__ */ H("button", {
						ref: c,
						type: "button",
						role: "menuitem",
						"aria-disabled": x,
						onClick: () => {
							x || T(y);
						},
						children: [/* @__PURE__ */ H(xc, {}), /* @__PURE__ */ H("span", { children: n.deleteSession })]
					})
				}) : null
			]
		})
	});
}
function ec(e) {
	let t = new Map((e.sessions?.sessions ?? []).map((e) => [e.sessionId, e])), n = new Set(e.loadedSessions.map((e) => e.sessionId));
	return [...e.loadedSessions.map((e) => ({
		...t.get(e.sessionId),
		...e,
		loaded: e
	})), ...(e.sessions?.sessions ?? []).filter((e) => !n.has(e.sessionId))];
}
function tc(e) {
	let t = e?.getRootNode();
	return t instanceof Document || t instanceof ShadowRoot ? t.activeElement : document.activeElement;
}
var nc = new Ja({
	gfm: !0,
	breaks: !0
}), rc = "a[href], button, input, select, textarea, [tabindex]:not([tabindex=\"-1\"])", ic = new Wa();
ic.html = ({ text: e }) => sc(e), ic.image = ({ text: e }) => `<span class="paui-markdown-image-alt">${sc(e)}</span>`, ic.checkbox = ({ checked: e }) => e ? "[x] " : "[ ] ", ic.table = function(e) {
	return `<div class="paui-markdown-table">${Wa.prototype.table.call(this, e)}</div>`;
}, ic.link = ({ href: e, title: t, tokens: n }) => {
	let r = sc(n.map((e) => e.raw).join(""));
	return cc(e) ? `<a href="${oc(e)}" target="_blank" rel="noopener noreferrer"${t ? ` title="${oc(t)}"` : ""}>${r}</a>` : r;
}, nc.use({ renderer: ic });
function ac(e) {
	let t = nc.parse(e);
	return pi.sanitize(t, {
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
function oc(e) {
	return sc(e).replaceAll("\"", "&quot;").replaceAll("'", "&#39;");
}
function sc(e) {
	return e.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}
function cc(e) {
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
function lc(e) {
	let t = is.get(e);
	if (t !== void 0) return t;
	let n = ++as;
	return is.set(e, n), n;
}
function uc(e) {
	if (e.sessionId) return e.sessionInstanceId ? `${e.sessionId}\u0000${e.sessionInstanceId}` : e.sessionId;
}
function dc(e, t) {
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
function fc(e) {
	return e.some((e) => e.status === "in_progress") ? "in_progress" : e.length && e.every((e) => e.status === "completed") ? "completed" : "pending";
}
function pc(e) {
	switch (e.type) {
		case "tool": return e.status;
		case "plan": return fc(e.entries);
		case "terminal": return e.exited ? "completed" : "in_progress";
		case "message": return e.pending ? "pending" : void 0;
		case "unsupported": return "unsupported";
		case "context":
		case "notice": return;
	}
}
function mc(e, t = Date.now(), n = Za.sessionAge) {
	if (!e) return "";
	let r = new Date(e).valueOf();
	if (Number.isNaN(r)) return e;
	let i = 6e4, a = 60 * i, o = 24 * a, s = Math.max(0, t - r);
	return s < i ? n(0, "now") : s < a ? n(Math.floor(s / i), "minute") : s < o ? n(Math.floor(s / a), "hour") : s < 30 * o ? n(Math.floor(s / o), "day") : s < 365 * o ? n(Math.floor(s / (30 * o)), "month") : n(Math.floor(s / (365 * o)), "year");
}
function hc(e) {
	return typeof e == "object" && !!e && !Array.isArray(e);
}
function gc({ status: e }) {
	return /* @__PURE__ */ H("span", {
		className: "paui-status",
		"data-status": e,
		children: e.replaceAll("_", " ")
	});
}
function $({ children: e }) {
	return /* @__PURE__ */ H("svg", {
		viewBox: "0 0 20 20",
		"aria-hidden": "true",
		focusable: "false",
		children: e
	});
}
var _c = () => /* @__PURE__ */ H($, { children: /* @__PURE__ */ H("path", { d: "M3 10a7 7 0 1 0 2-4.9M3 3v4h4M10 6v4l3 2" }) }), vc = () => /* @__PURE__ */ H($, { children: /* @__PURE__ */ H("path", { d: "M4 4h8a3 3 0 0 1 3 3v4a3 3 0 0 1-3 3H8l-4 3v-3a3 3 0 0 1-1-2V7a3 3 0 0 1 3-3M10 7v5M7.5 9.5h5" }) }), yc = () => /* @__PURE__ */ H($, { children: /* @__PURE__ */ H("path", { d: "m5 5 10 10M15 5 5 15" }) }), bc = () => /* @__PURE__ */ H($, { children: [
	/* @__PURE__ */ H("circle", {
		cx: "5",
		cy: "10",
		r: "1",
		fill: "currentColor",
		stroke: "none"
	}),
	/* @__PURE__ */ H("circle", {
		cx: "10",
		cy: "10",
		r: "1",
		fill: "currentColor",
		stroke: "none"
	}),
	/* @__PURE__ */ H("circle", {
		cx: "15",
		cy: "10",
		r: "1",
		fill: "currentColor",
		stroke: "none"
	})
] }), xc = () => /* @__PURE__ */ H($, { children: /* @__PURE__ */ H("path", { d: "M4 6h12M8 3h4l1 3M6 6l1 11h6l1-11M9 9v5M12 9v5" }) }), Sc = () => /* @__PURE__ */ H("svg", {
	viewBox: "0 0 16 16",
	"aria-hidden": "true",
	focusable: "false",
	children: /* @__PURE__ */ H("path", {
		d: "M8.3125.9802c.3552.0729.6665.224 0.9502.4521.2245.1807.4676.4256.7168.6748L14.707 6.8347 13.293 8.2487 9 3.9558v11.0859H7V3.9558L2.707 8.2487 1.293 6.8347l4.7275-4.7276c.2492-.2492.4923-.4941.7168-.6748.2393-.1924.5471-.3883.9502-.4521.2098-.0332.4156-.025.625 0Z",
		fill: "currentColor"
	})
}), Cc = () => /* @__PURE__ */ H("svg", {
	viewBox: "0 0 16 16",
	"aria-hidden": "true",
	focusable: "false",
	children: /* @__PURE__ */ H("rect", {
		x: "3",
		y: "3",
		width: "10",
		height: "10",
		rx: "3",
		fill: "currentColor"
	})
}), wc = () => /* @__PURE__ */ H($, { children: /* @__PURE__ */ H("path", { d: "m5 8 5 5 5-5" }) }), Tc = () => /* @__PURE__ */ H($, { children: /* @__PURE__ */ H("path", { d: "m12.5 4.5-5 5 5 5" }) }), Ec = () => /* @__PURE__ */ H("svg", {
	viewBox: "0 0 14 14",
	"aria-hidden": "true",
	focusable: "false",
	children: /* @__PURE__ */ H("path", { d: "m4 5.5 3 3 3-3" })
}), Dc = () => /* @__PURE__ */ H("svg", {
	viewBox: "0 0 14 14",
	"aria-hidden": "true",
	focusable: "false",
	children: /* @__PURE__ */ H("path", { d: "m3 7 2.5 2.5L11 4" })
}), Oc = () => /* @__PURE__ */ H($, { children: /* @__PURE__ */ H("path", { d: "M12.5 4.2a4 4 0 0 0-5 5L3 13.7 6.3 17l4.5-4.5a4 4 0 0 0 5-5l-2.3 2.3-3.3-3.3 2.3-2.3Z" }) }), kc = () => /* @__PURE__ */ H($, { children: [
	/* @__PURE__ */ H("circle", {
		cx: "10",
		cy: "5",
		r: "2"
	}),
	/* @__PURE__ */ H("circle", {
		cx: "5",
		cy: "14",
		r: "2"
	}),
	/* @__PURE__ */ H("circle", {
		cx: "15",
		cy: "14",
		r: "2"
	}),
	/* @__PURE__ */ H("path", { d: "m8.8 6.7-2.6 5.6M11.2 6.7l2.6 5.6M7 14h6" })
] }), Ac = () => /* @__PURE__ */ H($, { children: /* @__PURE__ */ H("path", { d: "M5 5h5v5M10 5 4.5 10.5M9 9h6v6H9" }) }), jc = () => /* @__PURE__ */ H($, { children: /* @__PURE__ */ H("path", { d: "M6 5h10M6 10h10M6 15h10M3 5h.01M3 10h.01M3 15h.01" }) }), Mc = () => /* @__PURE__ */ H("svg", {
	className: "paui-think-icon",
	viewBox: "0 0 14 14",
	"aria-hidden": "true",
	focusable: "false",
	children: [/* @__PURE__ */ H("path", {
		d: "M7.06431 5.93342C7.68763 5.93342 8.19307 6.43904 8.19322 7.06233C8.19322 7.68573 7.68772 8.19123 7.06431 8.19123C6.44099 8.19113 5.9354 7.68567 5.9354 7.06233C5.93555 6.43911 6.44108 5.93353 7.06431 5.93342Z",
		fill: "currentColor"
	}), /* @__PURE__ */ H("path", {
		fillRule: "evenodd",
		clipRule: "evenodd",
		d: "M8.6815.963693c1.4354-.516674 2.9451-.588864 3.8818.347657.9367.9367.8644 2.44641.3477 3.88184-.1984.55112-.4724 1.12477-.8145 1.7041.4004.64909.7176 1.29289.9395 1.90918.5167 1.43543.5891 2.94513-.3477 3.88183-.9367.9367-2.4463.8644-3.8818.3477-.61628-.2219-1.26009-.5391-1.90918-.9395-.57935.3421-1.15297.616-1.7041.8145-1.43545.5166-2.94512.589-3.88184-.3477-.936521-.9367-.864331-2.4465-.347656-3.88188.208126-.57809.499486-1.18084.865236-1.78907-.30714-.53529-.55661-1.06415-.74024-1.57421C.572068 3.88278.499714 2.37306 1.43638 1.43635c.9367-.936695 2.44642-.864306 3.88184-.34766.51006.18363 1.03893.43311 1.57421.74024.60823-.36575 1.21098-.65712 1.78907-.865237ZM11.3573 8.01154c-.449.61099-.9672 1.21719-1.54787 1.79786-.58066.5807-1.18688 1.0989-1.79785 1.5478.41412.2269.81712.4115 1.20117.5499 1.33285.4797 2.21185.3476 2.62695-.0674.4151-.4151.5472-1.2941.0674-2.62698-.1383-.38406-.323-.78704-.5498-1.20118ZM2.56529 8.02912c-.19185.3641-.35034.71884-.47266 1.0586-.47972 1.33268-.34751 2.21178.06738 2.62698.41504.415 1.29414.5471 2.62696.0674.3236-.1165.66089-.2657 1.00683-.4454-.5448-.4144-1.08458-.8834-1.60351-1.4023-.61451-.61453-1.1586-1.25807-1.625-1.90528Zm4.34179-4.78222c-.66643.45789-1.34248 1.01631-1.99316 1.66699-.65067.65067-1.2091 1.32674-1.66699 1.99316.47981.7262 1.08084 1.46754 1.79199 2.17871.61051.61051 1.24291 1.14074 1.86914 1.58204.68562-.4653 1.38274-1.03704 2.05273-1.70704.67001-.67001 1.24171-1.3671 1.70701-2.05273-.4413-.62623-.97149-1.25863-1.58201-1.86914-.71117-.71116-1.45251-1.31217-2.17871-1.79199Zm4.80762-1.08692c-.4151-.41489-1.2943-.5471-2.62695-.06738-.3394.12219-.69393.28011-1.05762.47168.64715.46637 1.28982 1.01152 1.9043 1.62598.51897.51894.98787 1.0587 1.40237 1.60351.1796-.34592.3288-.68325.4453-1.00683.4797-1.33278.3476-2.21192-.0674-2.62696ZM4.91197 2.2176c-1.33275-.47972-2.21193-.34765-2.62696.06738-.415.41505-.5471 1.29422-.06738 2.62696.09946.27628.22349.56233.36914.85546.43254-.5787.92797-1.1516 1.47852-1.70214.55055-.55056 1.12343-1.04598 1.70214-1.47852-.29312-.14564-.57919-.26968-.85546-.36914Z",
		fill: "currentColor"
	})]
}), Nc = () => /* @__PURE__ */ H($, { children: /* @__PURE__ */ H("path", { d: "M5 3h10v14H5zM8 7h4M8 10h4" }) }), Pc = () => /* @__PURE__ */ H($, { children: [/* @__PURE__ */ H("circle", {
	cx: "8.5",
	cy: "8.5",
	r: "5.5"
}), /* @__PURE__ */ H("path", { d: "m12.5 12.5 4 4" })] }), Fc = () => /* @__PURE__ */ H($, { children: /* @__PURE__ */ H("path", { d: "m4 6 4 4-4 4M10 14h6" }) }), Ic = () => /* @__PURE__ */ H($, { children: /* @__PURE__ */ H("path", { d: "M10 2 16 5v5c0 4-2.5 6.5-6 8-3.5-1.5-6-4-6-8V5l6-3Zm-2 8 1.5 1.5L13 8" }) }), Lc = () => /* @__PURE__ */ H($, { children: /* @__PURE__ */ H("path", { d: "M8 12 12 8M6.5 13.5l-1 1a3 3 0 0 1-4-4l3-3a3 3 0 0 1 4 0M13.5 6.5l1-1a3 3 0 0 1 4 4l-3 3a3 3 0 0 1-4 0" }) }), Rc = () => /* @__PURE__ */ H($, { children: /* @__PURE__ */ H("path", { d: "M5 2h7l4 4v12H5V2Zm7 0v5h4" }) }), zc = () => /* @__PURE__ */ H($, { children: /* @__PURE__ */ H("path", { d: "M5 3v14M3 5l2-2 2 2M15 17V3M13 15l2 2 2-2M9 7h3M9 13h3" }) }), Bc = () => /* @__PURE__ */ H($, { children: /* @__PURE__ */ H("path", { d: "M6 5h10v10H6zM3 8v9h9" }) }), Vc = () => /* @__PURE__ */ H($, { children: [/* @__PURE__ */ H("circle", {
	cx: "10",
	cy: "10",
	r: "7"
}), /* @__PURE__ */ H("path", { d: "M10 9v5M10 6h.01" })] }), Hc = () => /* @__PURE__ */ H($, { children: [/* @__PURE__ */ H("path", { d: "M10 2 19 18H1L10 2Z" }), /* @__PURE__ */ H("path", { d: "M10 7v5M10 15h.01" })] }), Uc = () => /* @__PURE__ */ H($, { children: /* @__PURE__ */ H("path", { d: "m10 2 1.5 4.5L16 8l-4.5 1.5L10 14l-1.5-4.5L4 8l4.5-1.5L10 2ZM15.5 13l.7 2.3 2.3.7-2.3.7-.7 2.3-.7-2.3-2.3-.7 2.3-.7.7-2.3Z" }) }), Wc = () => /* @__PURE__ */ H($, { children: /* @__PURE__ */ H("path", { d: "M4 3h12v14H4zM7 7h6M7 10h6M7 13h3" }) }), Gc = ".pretty-aui-standalone-root{box-sizing:border-box;width:100%;min-width:0;height:100%;min-height:0}.pretty-aui-standalone-root>.pretty-aui{height:100%;min-height:0}.pretty-aui{--paui-default-background:#fff;--paui-default-surface:#f7f8fa;--paui-default-surface-raised:#fff;--paui-default-user-bubble:#edf3fe;--paui-default-text:#0f1115;--paui-default-text-muted:#667085;--paui-default-border:#e5e7eb;--paui-default-accent:#4176e6;--paui-default-on-accent:#fff;--paui-default-accent-soft:#edf3fe;--paui-default-danger:#c63d4f;--paui-default-warning:#a86610;--paui-default-success:#24845b;--paui-default-action-hover:#679efe;--paui-default-flow-title:#61666b;--paui-default-flow-copy:#81858c;--paui-default-flow-caption:#adb2b8;--paui-background:var(--pretty-aui-color-background,var(--paui-default-background));--paui-surface:var(--pretty-aui-color-surface,var(--paui-default-surface));--paui-surface-raised:var(--pretty-aui-color-surface-raised,var(--paui-default-surface-raised));--paui-user-bubble:var(--pretty-aui-color-user-bubble,var(--paui-default-user-bubble));--paui-text:var(--pretty-aui-color-text,var(--paui-default-text));--paui-text-muted:var(--pretty-aui-color-text-muted,var(--paui-default-text-muted));--paui-border:var(--pretty-aui-color-border,var(--paui-default-border));--paui-accent:var(--pretty-aui-color-accent,var(--paui-default-accent));--paui-on-accent:var(--pretty-aui-color-on-accent,var(--paui-default-on-accent));--paui-accent-soft:var(--pretty-aui-color-accent-soft,var(--paui-default-accent-soft));--paui-danger:var(--pretty-aui-color-danger,var(--paui-default-danger));--paui-warning:var(--pretty-aui-color-warning,var(--paui-default-warning));--paui-success:var(--pretty-aui-color-success,var(--paui-default-success));--paui-action-hover:var(--paui-default-action-hover);--paui-flow-title:var(--pretty-aui-color-text-muted,var(--paui-default-flow-title));--paui-flow-copy:var(--pretty-aui-color-text-muted,var(--paui-default-flow-copy));--paui-flow-caption:var(--pretty-aui-color-text-muted,var(--paui-default-flow-caption));--paui-sans:var(--pretty-aui-font-sans,Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif);--paui-mono:var(--pretty-aui-font-mono,ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace);--paui-shadow-raised:var(--pretty-aui-shadow-raised,0 4px 12px 0 #00000005, 0 2px 8px 0 #0000000a);--paui-content-width:var(--pretty-aui-content-max-width,748px);--paui-composer-width:var(--pretty-aui-composer-max-width,780px);--paui-gutter:var(--pretty-aui-gutter,16px);box-sizing:border-box;width:100%;height:var(--pretty-aui-height,680px);min-width:0;min-height:var(--pretty-aui-min-height,420px);border:1px solid var(--paui-border);color:var(--paui-text);--lightningcss-light:initial;--lightningcss-dark: ;color-scheme:light;background:var(--paui-background);contain:layout style;font-family:var(--paui-sans);text-align:left;isolation:isolate;border-radius:14px;flex-direction:column;font-size:14px;line-height:1.5;display:flex;position:relative;overflow:clip;container:pretty-aui/inline-size}.pretty-aui[data-scheme=dark]{--paui-default-background:#151517;--paui-default-surface:#232324;--paui-default-surface-raised:#2c2c2e;--paui-default-user-bubble:#2c2c2e;--paui-default-text:#f9fafb;--paui-default-text-muted:#a4a7ae;--paui-default-border:#343438;--paui-default-accent:#679efe;--paui-default-on-accent:#0f1115;--paui-default-accent-soft:#202c43;--paui-default-danger:#f08a96;--paui-default-warning:#e6ab5e;--paui-default-success:#65c99c;--paui-default-action-hover:#8ab4ff;--paui-default-flow-title:#cfd3d6;--paui-default-flow-copy:#adb2b8;--paui-default-flow-caption:#81858c;--lightningcss-light: ;--lightningcss-dark:initial;color-scheme:dark}@media (prefers-color-scheme:dark){.pretty-aui[data-scheme=system]{--paui-default-background:#151517;--paui-default-surface:#232324;--paui-default-surface-raised:#2c2c2e;--paui-default-user-bubble:#2c2c2e;--paui-default-text:#f9fafb;--paui-default-text-muted:#a4a7ae;--paui-default-border:#343438;--paui-default-accent:#679efe;--paui-default-on-accent:#0f1115;--paui-default-accent-soft:#202c43;--paui-default-danger:#f08a96;--paui-default-warning:#e6ab5e;--paui-default-success:#65c99c;--paui-default-action-hover:#8ab4ff;--paui-default-flow-title:#cfd3d6;--paui-default-flow-copy:#adb2b8;--paui-default-flow-caption:#81858c;--lightningcss-light: ;--lightningcss-dark:initial;color-scheme:dark}}.pretty-aui *,.pretty-aui :before,.pretty-aui :after{box-sizing:border-box}.pretty-aui button,.pretty-aui input,.pretty-aui select,.pretty-aui textarea{color:inherit;font:inherit}.pretty-aui button{cursor:pointer}.pretty-aui :is(button,input,select,textarea):disabled{cursor:not-allowed;opacity:.46}.pretty-aui :is(button,input,select,textarea,summary,a,.paui-body,.paui-context-injection__body):focus-visible{outline:2px solid var(--paui-accent);outline-offset:2px}.pretty-aui svg{fill:none;stroke:currentColor;stroke-linecap:round;stroke-linejoin:round;stroke-width:1.6px;flex:none;width:18px;height:18px}.paui-header{z-index:4;border-bottom:1px solid var(--paui-border);background:color-mix(in srgb, var(--paui-background) 94%, transparent);-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px);justify-content:space-between;align-items:center;min-width:0;min-height:56px;padding:10px 14px 10px 18px;display:flex}.pretty-aui[data-surface=sidebar] .paui-header{min-height:48px;padding:7px 8px 7px 12px}.paui-identity,.paui-header__actions,.paui-interaction__actions,.paui-config{align-items:center;display:flex}.paui-identity{flex:auto;gap:10px;min-width:0}.paui-identity>div{min-width:0;display:grid}.paui-identity strong{letter-spacing:-.01em;text-overflow:ellipsis;white-space:nowrap;font-size:13px;font-weight:600;overflow:hidden}.paui-lineage{min-width:0;display:grid}.paui-lineage__titles{white-space:nowrap;align-items:center;gap:6px;min-width:0;display:flex}.paui-lineage__titles strong{text-overflow:ellipsis;min-width:0;overflow:hidden}.paui-lineage__ancestor{min-width:0;color:var(--paui-flow-caption);align-items:center;gap:6px;display:inline-flex}.paui-lineage__ancestor button{max-width:144px;color:var(--paui-text-muted);text-overflow:ellipsis;white-space:nowrap;background:0 0;border:0;padding:0;font-size:13px;overflow:hidden}.paui-lineage__ancestor button:hover:not(:disabled){color:var(--paui-text)}.paui-lineage__back{background:0 0;border:0;border-radius:7px;place-items:center;width:28px;height:28px;padding:0;display:none}.paui-lineage__back:hover:not(:disabled){background:var(--paui-surface)}.paui-lineage__back svg{width:16px;height:16px}.paui-protocol{color:var(--paui-text-muted);font-family:var(--paui-mono);letter-spacing:.02em;text-overflow:ellipsis;text-transform:uppercase;white-space:nowrap;font-size:10px;overflow:hidden}.pretty-aui[data-surface=sidebar] .paui-protocol{display:none}.paui-presence{border:2px solid var(--paui-background);background:var(--paui-text-muted);width:9px;height:9px;box-shadow:0 0 0 1px var(--paui-border);border-radius:50%;flex:none}.paui-presence[data-phase=idle]{background:var(--paui-success)}.paui-presence:is([data-phase=running],[data-phase=awaiting_user],[data-phase=cancelling]){background:var(--paui-accent);box-shadow:0 0 0 1px var(--paui-accent), 0 0 0 4px var(--paui-accent-soft)}.paui-header__actions{flex:none;gap:2px}.paui-icon-button,.paui-send,.paui-to-bottom{background:0 0;border:0;border-radius:10px;place-items:center;width:34px;height:34px;padding:0;display:inline-grid}.paui-icon-button:hover:not(:disabled){background:var(--paui-surface)}.paui-body{min-width:0;min-height:0;padding:24px var(--paui-gutter) 0;overscroll-behavior:contain;scrollbar-color:var(--paui-border) transparent;scrollbar-gutter:stable;flex:auto;position:relative;overflow:hidden auto}.paui-transcript{width:100%;max-width:var(--paui-content-width);gap:28px;margin:0 auto;padding-bottom:24px;display:grid}.paui-turn{gap:16px;min-width:0;display:grid}.paui-message{flex-direction:column;min-width:0;display:flex}.paui-message[data-role=user]{align-items:flex-end;gap:6px}.paui-message__bubble{min-width:0}.paui-message[data-role=user] .paui-message__bubble{background:var(--paui-user-bubble);border-radius:22px;max-width:min(525px,82%);padding:10px 16px}.paui-message[data-role=user][data-pending=true]{opacity:.68}.paui-message__label{display:none}.paui-message__content>:first-child,.paui-markdown>:first-child{margin-top:0}.paui-message__content>:last-child,.paui-markdown>:last-child{margin-bottom:0}.paui-markdown{overflow-wrap:anywhere;min-width:0;font-size:16px;line-height:28px}.paui-message[data-role=user] .paui-markdown{font-size:16px;line-height:24px}.paui-message__actions{align-items:center;gap:10px;height:28px;display:flex}.paui-message[data-role=assistant] .paui-message__actions{margin-top:16px;margin-left:-6px}.paui-message__action{width:28px;height:28px;color:var(--paui-text-muted);background:0 0;border:0;border-radius:50%;place-items:center;padding:6px;display:inline-grid}.pretty-aui .paui-message__action svg{width:16px;height:16px}.paui-message__action:hover{color:var(--paui-text);background:var(--paui-surface)}.paui-message__time{color:var(--paui-text-muted);opacity:0;white-space:nowrap;font-size:14px;line-height:24px;transition:opacity 80ms}.paui-message__time--start{padding-right:12px}.paui-message__time--end{padding-left:12px}.pretty-aui [data-time-hover-root]:hover .paui-message__time,.pretty-aui [data-time-hover-root]:focus-within .paui-message__time{opacity:1}.paui-markdown :is(p,ul,ol,pre,blockquote){margin:.72em 0}.paui-markdown :is(h1,h2,h3,h4){letter-spacing:-.015em;margin:1.15em 0 .45em;font-size:1em;font-weight:650}.paui-markdown :is(code),.paui-url,.paui-terminal pre,.paui-diff pre,.paui-resource pre{font-family:var(--paui-mono);font-size:.84em}.paui-markdown :not(pre)>code{background:var(--paui-surface);border-radius:5px;padding:.14em .35em}.paui-markdown pre,.paui-terminal pre,.paui-diff pre,.paui-resource pre{border:1px solid var(--paui-border);background:var(--paui-surface);white-space:pre;border-radius:9px;max-width:100%;padding:12px 14px;line-height:1.55;overflow:auto}.paui-markdown-table{box-sizing:border-box;border:1px solid var(--paui-border);scrollbar-color:var(--paui-border) transparent;border-radius:9px;max-width:100%;margin:.72em 0;overflow-x:auto}.paui-markdown-table table{border-collapse:collapse;width:max-content;min-width:100%;font-size:.9em;line-height:1.5}.paui-markdown-table :is(th,td){border-right:1px solid var(--paui-border);border-bottom:1px solid var(--paui-border);overflow-wrap:normal;vertical-align:top;min-width:8rem;padding:8px 10px}.paui-markdown-table th{background:var(--paui-surface);font-weight:650}.paui-markdown-table [align=left]{text-align:left}.paui-markdown-table [align=center]{text-align:center}.paui-markdown-table [align=right]{text-align:right}.paui-markdown-table tr:last-child td{border-bottom:0}.paui-markdown-table :is(th,td):last-child{border-right:0}.paui-markdown a,.paui-resource{color:var(--paui-accent);-webkit-text-decoration-color:color-mix(in srgb, var(--paui-accent) 45%, transparent);text-decoration-color:color-mix(in srgb, var(--paui-accent) 45%, transparent);text-underline-offset:3px}.paui-activities{gap:16px;min-width:0;display:grid}.paui-notice-group{gap:6px;min-width:0;display:grid}.paui-activity{min-width:0}.paui-host-notice{min-width:0;color:var(--paui-text-muted);overflow-wrap:anywhere;align-items:flex-start;gap:7px;padding:2px 0;font-size:13px;line-height:20px;display:flex}.paui-activity[data-kind=notice][data-level=error] .paui-host-notice{color:var(--paui-danger)}.paui-host-notice__icon{flex:none;place-items:center;width:16px;height:20px;display:inline-grid}.paui-host-notice__icon svg{width:14px;height:14px}.paui-thought,.paui-disclosure,.paui-diff,.paui-resource{min-width:0}.paui-thought>summary,.paui-disclosure>summary,.paui-diff>summary,.paui-resource>summary{min-height:28px;color:var(--paui-text-muted);cursor:pointer;border-radius:6px;align-items:center;gap:7px;font-size:13px;line-height:20px;list-style:none;display:flex}.paui-thought>summary:hover,.paui-disclosure>summary:hover{color:color-mix(in srgb, var(--paui-text) 78%, var(--paui-text-muted))}.pretty-aui summary::-webkit-details-marker{display:none}.paui-thought>summary svg,.paui-disclosure>summary svg,.paui-diff>summary svg,.paui-resource>summary svg{width:15px;height:15px}.paui-thought__body,.paui-disclosure__body{color:var(--paui-text-muted);padding:4px 0 4px 22px;font-size:14px;line-height:24px}.pretty-aui .paui-flow-summary{align-items:center;gap:0;min-width:0;height:24px;min-height:24px;line-height:24px;display:flex;position:relative;overflow:hidden}.paui-flow-leading{width:16px;height:16px;color:var(--paui-flow-copy);flex:none;justify-content:center;align-items:center;margin-right:6px;display:inline-flex;position:relative}.paui-flow-icon,.paui-flow-chevron{justify-content:center;align-items:center;transition:opacity .1s;display:inline-flex}.paui-flow-chevron{opacity:0;position:absolute;inset:0}.pretty-aui .paui-flow-leading svg{width:14px;height:14px}.pretty-aui .paui-flow-leading .paui-think-icon{fill:currentColor;stroke:none}.paui-flow-summary:hover .paui-flow-icon,.paui-thought[open] .paui-flow-icon,.paui-tool[open] .paui-flow-icon,.paui-context-injection[open] .paui-flow-icon{opacity:0}.paui-flow-summary:hover .paui-flow-chevron,.paui-thought[open] .paui-flow-chevron,.paui-tool[open] .paui-flow-chevron,.paui-context-injection[open] .paui-flow-chevron{opacity:1}.paui-flow-title{color:var(--paui-flow-title);flex:none;font-size:14px;font-weight:400;line-height:24px}.paui-flow-separator{background:var(--paui-flow-caption);border-radius:1px;flex:none;width:2px;height:2px;margin:0 8px}.paui-flow-preview{min-width:0;color:var(--paui-flow-copy);text-overflow:ellipsis;white-space:nowrap;flex:auto;font-size:14px;line-height:24px;overflow:hidden}.paui-flow-preview[data-follow-end=true]{text-overflow:clip}.paui-context-injection__body{box-sizing:border-box;width:calc(100% - 22px);max-height:141px;color:var(--paui-text-muted);background:var(--paui-surface);font:400 11px/16px var(--paui-mono);scrollbar-color:var(--paui-border) transparent;border-radius:8px;margin:4px 0 0 22px;padding:10px 12px 12px;overflow:auto}.paui-context-injection__body>*+*{margin-top:8px}.paui-context-block{gap:4px;min-width:0;display:grid}.paui-context-meta{min-width:0;color:var(--paui-text-muted);overflow-wrap:anywhere;flex-wrap:wrap;gap:4px 10px;display:flex}.paui-context-meta>span+span{color:var(--paui-flow-caption)}.paui-context-text{color:var(--paui-flow-copy);font:inherit;overflow-wrap:anywhere;white-space:pre-wrap;margin:0}.paui-context-identifier,.paui-context-truncated{color:var(--paui-flow-caption);overflow-wrap:anywhere}.paui-subagent-row{align-items:flex-start;gap:4px;width:100%;min-width:0;min-height:24px;display:flex}.paui-subagent{flex:auto;min-width:0}.paui-subagent-status{color:var(--paui-flow-caption);white-space:nowrap;flex:none;align-items:center;gap:8px;margin-left:12px;font-size:11px;line-height:24px;display:inline-flex}.paui-subagent-status__ongoing{align-items:center;gap:5px;display:inline-flex}.paui-subagent-status__spinner,.paui-session__spinner{border:1.5px solid color-mix(in srgb, var(--paui-accent) 28%, transparent);border-top-color:var(--paui-accent);border-radius:50%;width:9px;height:9px;animation:.8s linear infinite paui-subagent-spin}.paui-subagent-status[data-status=failed],.paui-subagent-status[data-status=cancelled],.paui-subagent:is([data-state=failed],[data-state=cancelled]) .paui-flow-leading{color:var(--paui-danger)}.paui-subagent-open{width:24px;height:24px;color:var(--paui-flow-copy);background:0 0;border:0;border-radius:6px;flex:none;place-items:center;padding:0;display:inline-grid}.paui-subagent-open:hover:not(:disabled){color:var(--paui-text);background:var(--paui-surface)}.paui-subagent-open svg{width:14px;height:14px}.paui-subagent[open] .paui-flow-icon{opacity:0}.paui-subagent[open] .paui-flow-chevron{opacity:1}@keyframes paui-subagent-spin{to{transform:rotate(360deg)}}.paui-thought[open] .paui-flow-separator,.paui-thought[open] .paui-flow-preview{display:none}.paui-tool[data-state=failed] .paui-flow-leading{color:var(--paui-danger)}.paui-thought[data-running=true]>.paui-flow-summary:after,.paui-tool:is([data-state=pending],[data-state=in_progress])>.paui-flow-summary:after{inset-block:0;background:linear-gradient(90deg, transparent 0%, color-mix(in srgb, var(--paui-background) 60%, transparent) 55%, transparent 100%);content:\"\";pointer-events:none;width:300px;animation:2.6s ease-out infinite paui-flow-sweep;position:absolute;left:0}@keyframes paui-flow-sweep{0%{left:-300px}90%,to{left:100%}}@media (prefers-reduced-motion:reduce){.paui-thought[data-running=true]>.paui-flow-summary:after,.paui-tool:is([data-state=pending],[data-state=in_progress])>.paui-flow-summary:after{animation:none}.paui-subagent-status__spinner,.paui-session__spinner{border-color:var(--paui-accent);background:var(--paui-accent);animation:none}}.paui-status{color:var(--paui-text-muted);font-family:var(--paui-mono);letter-spacing:.04em;text-transform:uppercase;margin-left:auto;font-size:9px}.paui-status:is([data-status=failed],[data-status=cancelled]){color:var(--paui-danger)}.paui-plan__list{gap:6px;margin:4px 0 0;padding:4px 0 4px 22px;list-style:none;display:grid}.paui-plan__list li{color:var(--paui-text-muted);grid-template-columns:12px 1fr;align-items:start;gap:8px;font-size:13px;line-height:20px;display:grid}.paui-plan__mark{border:1px solid;border-radius:50%;width:7px;height:7px;margin-top:6px}.paui-plan__list li[data-status=completed] .paui-plan__mark{border-color:var(--paui-success);background:var(--paui-success)}.paui-plan__list li[data-status=in_progress]{color:var(--paui-text)}.paui-plan__list li[data-status=in_progress] .paui-plan__mark{border-color:var(--paui-accent);background:var(--paui-accent);box-shadow:inset 0 0 0 2px var(--paui-background)}.paui-media{border-radius:10px;max-width:100%;max-height:420px;margin:10px 0;display:block}.paui-resource{align-items:center;gap:6px;display:inline-flex}.paui-resource svg{width:15px;height:15px}.paui-unsupported,.paui-muted{color:var(--paui-text-muted);font-size:12px}.paui-notice{background:var(--paui-accent-soft);border-radius:9px;align-items:center;gap:10px;padding:10px 12px;display:flex}.paui-notice>div,.paui-error>div{flex:1;min-width:0;display:grid}.paui-notice strong,.paui-error strong{font-size:12px}.paui-notice span,.paui-error span{color:var(--paui-text-muted);font-size:11px}.paui-notice svg,.paui-error svg{width:16px}.paui-empty{max-width:340px;color:var(--paui-text-muted);text-align:center;justify-items:center;margin:clamp(42px,12vh,90px) auto;display:grid}.paui-empty svg{width:24px;height:24px;color:var(--paui-accent);margin-bottom:12px}.paui-empty strong{color:var(--paui-text);letter-spacing:-.01em;font-size:16px;font-weight:600}.paui-empty p{margin:5px 0 0;font-size:12px}.paui-interactions{z-index:3;min-width:0;padding:0 var(--paui-gutter);background:var(--paui-background);gap:8px;display:grid}.paui-interactions:empty{display:none}.paui-error,.paui-interaction,.paui-auth{width:100%;max-width:var(--paui-content-width);border:1px solid var(--paui-border);background:var(--paui-surface);border-radius:12px;gap:11px;margin:0 auto;display:flex}.paui-error{border-color:color-mix(in srgb, var(--paui-danger) 30%, var(--paui-border));align-items:center;padding:10px 12px}.paui-error button,.paui-auth button,.paui-load-more{border:1px solid var(--paui-border);background:var(--paui-background);border-radius:8px;padding:6px 10px;font-size:12px}.paui-interaction{padding:14px}.paui-interaction__icon{width:28px;height:28px;color:var(--paui-accent);background:var(--paui-accent-soft);border-radius:8px;flex:none;place-items:center;display:grid}.paui-interaction__icon svg{width:16px}.paui-interaction__content{flex:1;gap:8px;min-width:0;display:grid}.paui-interaction__content>strong{font-size:13px}.paui-interaction__content>p{color:var(--paui-text-muted);margin:-3px 0 0;font-size:12px}.paui-interaction__actions{flex-wrap:wrap;gap:6px}.paui-button-primary,.paui-button-secondary,.paui-button-ghost{border-radius:8px;min-height:30px;padding:5px 10px;font-size:12px}.paui-button-primary{border:1px solid var(--paui-accent);color:var(--paui-on-accent);background:var(--paui-accent)}.paui-button-secondary{border:1px solid var(--paui-border);background:var(--paui-background)}.paui-button-ghost{color:var(--paui-text-muted);background:0 0;border:1px solid #0000}.paui-url{border:1px solid var(--paui-border);background:var(--paui-background);text-overflow:ellipsis;white-space:nowrap;border-radius:7px;padding:7px 8px;overflow:hidden}.paui-fields{gap:10px;display:grid}.paui-field{color:var(--paui-text-muted);gap:4px;font-size:11px;display:grid}.paui-field input,.paui-field select{border:1px solid var(--paui-border);min-height:34px;color:var(--paui-text);background:var(--paui-background);border-radius:7px;padding:6px 8px}.paui-field small{font-size:10px}.paui-field--check{align-items:center;display:flex}.paui-auth{justify-items:start;padding:16px;display:grid}.paui-auth>div{gap:6px;display:flex}.paui-auth>svg{color:var(--paui-accent)}.paui-composer-wrap{z-index:3;width:100%;padding:36px var(--paui-gutter) 8px;background:linear-gradient(to bottom, color-mix(in srgb, var(--paui-background) 0%, transparent) 0, var(--paui-background) 36px);justify-items:center;gap:6px;display:grid;position:relative}.paui-composer-wrap[data-placement=hero]{transition:top .18s,transform .18s;position:absolute;top:50%;left:0;transform:translateY(-10%)}.paui-composer{width:100%;max-width:var(--paui-composer-width);background:var(--paui-surface-raised);box-shadow:var(--paui-shadow-raised);border:0;border-radius:22px;flex-direction:column;gap:12px;padding:10px 8px 6px 16px;font-size:16px;line-height:24px;transition:box-shadow .12s;display:flex;position:relative}.paui-composer__context{scrollbar-width:thin;flex-wrap:wrap;align-items:center;gap:6px;min-width:0;max-height:68px;padding-right:4px;display:flex;overflow-y:auto}.pretty-aui .paui-context-add{width:22px;height:22px;color:var(--paui-text-muted);background:0 0;border:0;border-radius:6px;flex:0 0 22px;place-items:center;padding:0;font-size:17px;line-height:1;display:inline-grid}.pretty-aui .paui-context-add:hover:not(:disabled){color:var(--paui-text);background:var(--paui-surface)}.paui-context-chip{border:1px solid var(--paui-border);min-width:0;max-width:min(260px,100% - 28px);color:var(--paui-text);background:var(--paui-background);border-radius:7px;align-items:center;gap:4px;padding:2px 3px 2px 8px;font-size:11px;line-height:18px;display:inline-flex}.paui-context-chip__label{text-overflow:ellipsis;white-space:nowrap;overflow:hidden}.pretty-aui .paui-context-chip button{width:18px;height:18px;color:var(--paui-text-muted);background:0 0;border:0;border-radius:5px;flex:0 0 18px;place-items:center;padding:0;font-size:14px;line-height:1;display:inline-grid}.pretty-aui .paui-context-chip button:hover:not(:disabled){color:var(--paui-text);background:var(--paui-surface)}.paui-composer textarea{resize:none;background:0 0;border:0;outline:0;width:100%;min-height:24px;max-height:336px;padding:2px 0;line-height:24px;overflow-y:auto}.pretty-aui .paui-composer textarea:focus-visible{outline:0}.paui-composer-wrap[data-placement=hero] .paui-composer textarea{min-height:52px}.paui-composer textarea::placeholder{color:var(--paui-text-muted)}.paui-composer__actions{justify-content:space-between;align-items:center;width:100%;min-width:0;display:flex}.pretty-aui .paui-send{color:var(--paui-on-accent);background:var(--paui-accent);border-radius:999px;transition:background-color .1s;transform:translateY(-2px)}.pretty-aui .paui-send:hover:not(:disabled){background:var(--paui-action-hover)}.pretty-aui .paui-send:disabled{opacity:.4}.pretty-aui .paui-send svg{stroke:none;width:16px;height:16px}.pretty-aui .paui-stop{color:#fff;background:var(--paui-accent)}.paui-config{width:auto;min-height:20px;color:var(--paui-text-muted);gap:8px;font-size:10px}.paui-config label{align-items:center;gap:4px;display:inline-flex}.paui-config__field{min-width:0;position:relative}.pretty-aui .paui-config__trigger{max-width:min(220px,45cqw);min-height:20px;color:var(--paui-text-muted);background:0 0;border:0;border-radius:6px;outline:0;align-items:center;gap:3px;padding:1px 4px;font-size:10px;line-height:16px;text-decoration:none;display:inline-flex}.paui-config__trigger>span{text-overflow:ellipsis;white-space:nowrap;min-width:0;overflow:hidden}.pretty-aui .paui-config__trigger>svg{width:12px;height:12px;color:var(--paui-text-muted);transition:transform .12s}.pretty-aui .paui-config__trigger[aria-expanded=true]>svg{transform:rotate(180deg)}.pretty-aui .paui-config__trigger:hover:not(:disabled),.pretty-aui .paui-config__trigger:focus-visible,.pretty-aui .paui-config__trigger[aria-expanded=true]{color:var(--paui-text-muted);background:var(--paui-surface);outline:0;text-decoration:none}.paui-config__listbox{--paui-config-scrollbar:color-mix(in srgb, var(--paui-text-muted) 34%, transparent);--paui-config-scrollbar-hover:color-mix(in srgb, var(--paui-text-muted) 56%, transparent);z-index:20;overscroll-behavior:contain;width:max-content;min-width:min(220px,100cqw - 32px);max-width:min(360px,100cqw - 32px);max-height:min(320px,100vh - 96px);color:var(--paui-text);background:var(--paui-surface-raised);box-shadow:0 16px 40px #0000001f, var(--paui-shadow-raised);border:0;border-radius:12px;padding:4px;font-size:12px;line-height:20px;position:absolute;bottom:calc(100% + 8px);left:0;overflow:hidden auto}@supports not selector(::-webkit-scrollbar){.paui-config__listbox{scrollbar-width:thin;scrollbar-color:var(--paui-config-scrollbar) transparent}}.paui-config__listbox::-webkit-scrollbar{width:8px;height:8px}.paui-config__listbox::-webkit-scrollbar-track{background:0 0}.paui-config__listbox::-webkit-scrollbar-corner{background:0 0}.paui-config__listbox::-webkit-scrollbar-thumb{background:var(--paui-config-scrollbar);background-clip:padding-box;border:2px solid #0000;border-radius:999px}.paui-config__listbox::-webkit-scrollbar-thumb:hover{background:var(--paui-config-scrollbar-hover);background-clip:padding-box}.pretty-aui .paui-config__option{width:100%;min-height:32px;color:var(--paui-text);text-align:left;background:0 0;border:0;border-radius:8px;outline:0;align-items:center;gap:8px;padding:6px 8px;display:flex}.paui-config__option>span:first-child{text-overflow:ellipsis;white-space:nowrap;flex:auto;min-width:0;overflow:hidden}.pretty-aui .paui-config__option[data-active=true],.pretty-aui .paui-config__option:focus-visible{background:var(--paui-surface);outline:0}.paui-config__check{width:16px;height:16px;color:var(--paui-text);flex:0 0 16px;place-items:center;display:inline-grid}.pretty-aui .paui-config__check svg{width:14px;height:14px}.paui-commands{right:var(--paui-gutter);bottom:calc(100% - 30px);left:var(--paui-gutter);max-width:var(--paui-composer-width);overscroll-behavior:contain;border:1px solid var(--paui-border);background:var(--paui-surface-raised);max-height:320px;box-shadow:var(--paui-shadow-raised);border-radius:12px;margin:0 auto;display:grid;position:absolute;overflow:hidden auto}.paui-commands button{border:0;border-bottom:1px solid var(--paui-border);text-align:left;background:0 0;grid-template-columns:minmax(110px,auto) 1fr;gap:10px;padding:8px 10px;display:grid}.paui-commands button:hover,.paui-commands button[aria-selected=true]{background:var(--paui-surface)}.paui-commands button:last-child{border-bottom:0}.paui-commands code{color:var(--paui-accent);font-family:var(--paui-mono);font-size:11px}.paui-commands span{color:var(--paui-text-muted);font-size:11px}.paui-to-bottom{border:1px solid var(--paui-border);background:var(--paui-surface-raised);box-shadow:var(--paui-shadow-raised);border-radius:50%}.paui-to-bottom-row{flex:none;place-items:center;height:46px;display:grid}.paui-drawer-backdrop{z-index:20;background:0 0;justify-content:flex-end;display:flex;position:absolute;inset:0}.paui-drawer{border-left:1px solid var(--paui-border);background:var(--paui-background);width:min(340px,88%);height:100%;min-height:0;box-shadow:var(--paui-shadow-raised);grid-template-rows:auto minmax(0,1fr);display:grid;position:relative}.paui-drawer>header{border-bottom:1px solid var(--paui-border);justify-content:space-between;align-items:center;min-height:56px;padding:10px 12px 10px 16px;display:flex}.paui-session-list{overscroll-behavior:contain;scrollbar-color:var(--paui-border) transparent;scrollbar-gutter:stable;align-content:start;gap:2px;min-height:0;padding:8px;display:grid;overflow-y:auto}.paui-session{box-sizing:border-box;border-radius:8px;grid-template-columns:minmax(0,1fr) auto;align-items:center;height:32px;padding:0 4px 0 8px;transition:background-color .1s;display:grid}.paui-session:is(:hover,:focus-within,[data-active=true],[data-menu-open=true]){background:var(--paui-surface)}.paui-session__select{min-width:0;height:100%;color:var(--paui-text);text-align:left;background:0 0;border:0;align-items:center;gap:4px;padding:0;display:flex}.pretty-aui .paui-session__select:disabled{cursor:default;opacity:1}.paui-session__title{text-overflow:ellipsis;white-space:nowrap;min-width:0;font-size:14px;font-weight:400;line-height:20px;overflow:hidden}.paui-session__spinner{flex:none}.paui-session__trailing{place-items:center end;min-width:32px;max-width:152px;display:grid;overflow:hidden}.paui-session__trailing>*{grid-area:1/1}.paui-session__meta{pointer-events:none;min-width:0;color:var(--paui-text-muted);text-overflow:ellipsis;white-space:nowrap;align-items:center;font-size:12px;line-height:20px;transition:opacity .1s;display:flex;overflow:hidden}.paui-session__meta>span:not(.paui-session__meta-separator){text-overflow:ellipsis;min-width:0;overflow:hidden}.paui-session__meta-separator{flex:none;margin:0 5px}.paui-session__action{width:32px;height:32px;color:var(--paui-text-muted);opacity:0;pointer-events:none;background:0 0;border:0;place-items:center;padding:0;transition:color .1s,opacity .1s;display:inline-grid}.paui-session__action svg{width:16px;height:16px}.paui-session__action:hover:not(:disabled){color:var(--paui-text)}.paui-session[data-has-actions=true]:is(:hover,:focus-within,[data-menu-open=true]) .paui-session__meta{opacity:0}.paui-session[data-has-actions=true]:is(:hover,:focus-within,[data-menu-open=true]) .paui-session__action{opacity:1;pointer-events:auto}.paui-session-menu{z-index:2;box-sizing:border-box;border:1px solid var(--paui-border);background:var(--paui-surface-raised);width:min(164px,100% - 16px);box-shadow:var(--paui-shadow-raised);border-radius:12px;padding:4px;display:grid;position:absolute}.paui-session-menu>button{width:100%;min-height:34px;color:var(--paui-danger);text-align:left;background:0 0;border:0;border-radius:8px;align-items:center;gap:8px;padding:6px 8px;font-size:13px;line-height:20px;display:flex}.paui-session-menu>button span{text-overflow:ellipsis;white-space:nowrap;min-width:0;overflow:hidden}.paui-session-menu>button:hover:not([aria-disabled=true]){background:color-mix(in srgb, var(--paui-danger) 10%, transparent)}.paui-session-menu>button[aria-disabled=true]{cursor:not-allowed;opacity:.46}.paui-session-menu svg{width:16px;height:16px}@media (hover:none){.paui-session[data-has-actions=true] .paui-session__meta{opacity:0}.paui-session[data-has-actions=true] .paui-session__action{opacity:1;pointer-events:auto}}@media (prefers-reduced-motion:reduce){.paui-session,.paui-session__action,.paui-session__meta{transition:none}}.paui-usage{max-width:156px;color:var(--paui-text-muted);font-family:var(--paui-mono);text-overflow:ellipsis;white-space:nowrap;font-size:10px;overflow:hidden}.paui-tool-block{box-sizing:border-box;border:1px solid var(--paui-border);width:100%;min-width:0;color:var(--paui-text);background:color-mix(in srgb, var(--paui-surface) 72%, transparent);font:400 12px/20px var(--paui-mono);border-radius:12px;overflow:hidden}.paui-tool-block__banner,.paui-tool-terminal__header,.paui-tool-io__section-header{justify-content:space-between;align-items:flex-start;gap:12px;min-width:0;display:flex}.paui-tool-block__banner{border-bottom:1px solid var(--paui-border);background:color-mix(in srgb, var(--paui-surface-raised) 36%, transparent);padding:9px 14px}.paui-tool-block__label{text-overflow:ellipsis;white-space:nowrap;min-width:0;overflow:hidden}.paui-tool-block__copy,.paui-tool-block__fold{color:var(--paui-text-muted);font:500 12px/20px var(--paui-sans);background:0 0;border:0;padding:0}.paui-tool-block__copy{flex:none}.paui-tool-block__copy:hover,.paui-tool-block__fold:hover{color:var(--paui-text)}.paui-tool-block__fold{border-block:1px solid var(--paui-border);text-align:left;width:100%;padding:5px 14px;display:block}.paui-tool-block__empty{color:var(--paui-text-muted);padding:12px 14px}.paui-tool-terminal__header{scrollbar-color:var(--paui-border) transparent;max-height:152px;padding:9px 14px 9px 30px;overflow:auto}.paui-tool-terminal:not([data-state=running]) .paui-tool-terminal__header{border-bottom:1px solid var(--paui-border)}.paui-tool-terminal__prompt{flex:1;min-width:max-content}.paui-tool-terminal__prompt-line{white-space:pre;align-items:baseline;gap:9px;min-width:0;display:flex;position:relative}.paui-tool-terminal__state{background:var(--paui-success);border-radius:50%;width:7px;height:7px;position:absolute;top:7px;left:-18px}.paui-tool-terminal[data-state=running] .paui-tool-terminal__state{background:var(--paui-accent);box-shadow:0 0 0 3px var(--paui-accent-soft);animation:1.5s ease-in-out infinite paui-pulse}@keyframes paui-pulse{50%{opacity:.48}}.paui-tool-terminal[data-state=failed] .paui-tool-terminal__state{background:var(--paui-danger)}.paui-tool-terminal__cwd{color:var(--paui-text-muted);flex:none}.paui-tool-terminal__command,.paui-tool-read__content,.paui-tool-diff__line{white-space:pre}.paui-tool-terminal__output{box-sizing:border-box;width:100%;max-height:224px;color:var(--paui-text);font:inherit;scrollbar-color:var(--paui-border) transparent;white-space:pre;background:0 0;margin:0;padding:12px 14px 12px 30px;overflow:auto}.paui-tool-terminal[data-state=failed] .paui-tool-terminal__output{color:var(--paui-danger)}.paui-tool-read__body,.paui-tool-diff__body{scrollbar-color:var(--paui-border) transparent;max-height:286px;overflow:auto}.paui-tool-read__line{grid-template-columns:minmax(38px,max-content) max-content;width:max-content;min-width:100%;display:grid}.paui-tool-read__gutter{color:var(--paui-text-muted);text-align:right;-webkit-user-select:none;user-select:none;padding:0 12px 0 8px}.paui-tool-read__content{padding-right:16px}.paui-tool-diff__line{box-sizing:border-box;width:max-content;min-width:100%;padding:0 14px}.paui-tool-diff__line[data-line-kind=add]{color:color-mix(in srgb, var(--paui-success) 88%, var(--paui-text));background:color-mix(in srgb, var(--paui-success) 11%, transparent)}.paui-tool-diff__line[data-line-kind=delete]{color:color-mix(in srgb, var(--paui-danger) 88%, var(--paui-text));background:color-mix(in srgb, var(--paui-danger) 10%, transparent)}.paui-tool-diff__line[data-line-kind=meta]{color:var(--paui-text-muted)}.paui-tool-diff__footer{border-top:1px solid var(--paui-border);color:var(--paui-text-muted);padding:6px 14px;font-size:11px}.paui-tool-io__section{scrollbar-color:var(--paui-border) transparent;max-height:190px;overflow:auto}.paui-tool-io__section-header{z-index:1;color:var(--paui-text-muted);background:var(--paui-surface);font:600 10px/18px var(--paui-sans);letter-spacing:.06em;text-transform:uppercase;padding:7px 14px;position:sticky;top:0}.paui-tool-io__section[data-error=true] .paui-tool-io__section-header,.paui-tool-io__section[data-error=true] .paui-tool-io__content{color:var(--paui-danger)}.paui-tool-io__content{min-width:max-content;padding:8px 14px 12px}.paui-tool-io__content pre{color:inherit;font:inherit;white-space:pre;margin:0}.paui-tool-io__divider{border-top:1px solid var(--paui-border);display:block}.paui-tool-supplementary{margin-top:8px}@media (prefers-reduced-motion:reduce){.paui-tool-terminal[data-state=running] .paui-tool-terminal__state{animation:none}}.paui-load-more{margin-top:6px}.paui-error-text{color:var(--paui-danger);padding:8px;font-size:11px}.paui-sr-only{clip:rect(0, 0, 0, 0);white-space:nowrap;border:0;width:1px;height:1px;padding:0;position:absolute;overflow:hidden}@container pretty-aui (width<=560px){.paui-header{min-height:48px;padding:7px 8px 7px 12px}.paui-identity--child{gap:4px}.paui-identity--child .paui-presence,.paui-lineage__ancestor{display:none}.paui-lineage{align-items:center;display:flex}.paui-lineage__back{display:inline-grid}.paui-lineage__titles{flex:auto;min-width:0}.paui-body{padding-top:18px}.paui-transcript{padding-bottom:18px}.paui-message[data-role=user] .paui-message__bubble{max-width:88%}.paui-markdown{font-size:15px;line-height:25px}.paui-message[data-role=user] .paui-markdown{font-size:15px;line-height:23px}.paui-interaction__actions{align-items:stretch}.paui-button-primary,.paui-button-secondary,.paui-button-ghost{flex:auto}.paui-composer-wrap{padding-left:10px;padding-right:10px}.paui-composer{padding-left:14px}}.pretty-aui[data-surface=sidebar] .paui-identity--child{gap:4px}.pretty-aui[data-surface=sidebar] :is(.paui-identity--child .paui-presence,.paui-lineage__ancestor){display:none}.pretty-aui[data-surface=sidebar] .paui-lineage{align-items:center;display:flex}.pretty-aui[data-surface=sidebar] .paui-lineage__back{display:inline-grid}@container pretty-aui (width<=380px){.paui-identity{gap:7px}.paui-protocol{display:none}.paui-message[data-role=user] .paui-message__bubble{max-width:92%}.paui-interaction{padding:11px}.paui-interaction__icon{display:none}}@media (prefers-reduced-motion:reduce){.pretty-aui *,.pretty-aui :before,.pretty-aui :after{scroll-behavior:auto!important;transition-duration:.01ms!important;animation-duration:.01ms!important;animation-iteration-count:1!important}}.paui-composer-menu{flex-shrink:0;position:relative}.paui-composer-menu__panel{z-index:20;border:1px solid var(--paui-border);background:var(--paui-surface);border-radius:12px;gap:2px;min-width:180px;max-width:min(320px,80cqw);max-height:240px;padding:6px;display:grid;position:absolute;bottom:calc(100% + 8px);left:0;overflow-y:auto;box-shadow:0 8px 24px #0002}.paui-composer-menu__panel button{text-align:start;white-space:normal;padding:8px 10px}.paui-composer-images{flex-wrap:wrap;gap:8px;padding:8px;display:flex}.paui-composer-images img{object-fit:contain;width:48px;height:48px}.paui-composer-images small{flex-basis:100%}", Kc = "Acp-Connection-Id", qc = "Acp-Session-Id", Jc = "text/event-stream", Yc = "application/json";
r.session_cancel, r.session_close, r.session_delete, r.session_fork, r.session_load, r.session_prompt, r.session_resume, r.session_set_config_option, r.session_set_mode, r.nes_suggest, r.nes_accept, r.nes_reject, r.nes_close, r.document_did_open, r.document_did_change, r.document_did_close, r.document_did_save, r.document_did_focus;
function Xc(e) {
	if (!h(e)) return;
	let t = e.sessionId;
	return typeof t == "string" ? t : void 0;
}
function Zc(e) {
	return "method" in e ? Xc(e.params) : void 0;
}
function Qc(e) {
	if (!m(e) || !("result" in e) || !h(e.result)) return;
	let t = e.result.sessionId;
	return typeof t == "string" ? t : void 0;
}
function $c(e) {
	return e.jsonrpc === "2.0" && "id" in e && "method" in e && e.method === r.initialize;
}
function el(e) {
	if (typeof e == "string") return `string:${e}`;
	if (typeof e == "number") return `number:${e}`;
	if (e === null) return "null";
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/cookie-store.js
var tl = class {
	cookies = /* @__PURE__ */ new Map();
	store(e) {
		for (let t of nl(e)) {
			let e = il(t);
			e && this.cookies.set(e.name, e.value);
		}
	}
	apply(e) {
		let t = al(this.cookieHeader(), e.get("Cookie"));
		t && e.set("Cookie", t);
	}
	clear() {
		this.cookies.clear();
	}
	cookieHeader() {
		return this.cookies.size === 0 ? void 0 : Array.from(this.cookies).map(([e, t]) => `${e}=${t}`).join("; ");
	}
};
function nl(e) {
	let t = e.getSetCookie;
	if (typeof t == "function") return t.call(e).flatMap(rl);
	let n = e.get("Set-Cookie");
	return n ? rl(n) : [];
}
function rl(e) {
	return e.split(/,(?=\s*[^;,\s]+=)/).map((e) => e.trim()).filter((e) => e.length > 0);
}
function il(e) {
	let t = e.split(";", 1)[0], n = t.indexOf("=");
	if (n <= 0) return;
	let r = t.slice(0, n).trim();
	if (r) return {
		name: r,
		value: t.slice(n + 1).trim()
	};
}
function al(e, t) {
	let n = /* @__PURE__ */ new Map();
	for (let t of ol(e)) n.set(t.name, t.value);
	for (let e of ol(t ?? void 0)) n.set(e.name, e.value);
	return n.size === 0 ? void 0 : Array.from(n).map(([e, t]) => `${e}=${t}`).join("; ");
}
function ol(e) {
	return e ? e.split(";").map(sl).filter((e) => e !== void 0) : [];
}
function sl(e) {
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
async function* cl(e) {
	let t = new TextDecoder(), n = e.getReader(), r = new Jt(), i = [], a = (e) => {
		let n = t.decode(e);
		return n.endsWith("\r") ? n.slice(0, -1) : n;
	}, o = () => {
		if (i.length === 0) return;
		let e = i;
		return i = [], ll(e);
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
function ll(e) {
	let t = e.filter((e) => e.startsWith("data:")).map((e) => {
		let t = e.slice(5);
		return t.startsWith(" ") ? t.slice(1) : t;
	});
	if (t.length === 0) return;
	let n = t.join("\n");
	if (n.trim()) try {
		let e = JSON.parse(n);
		if (h(e) || Array.isArray(e)) return e;
		console.warn("Skipping SSE payload that is not an object or array");
		return;
	} catch (e) {
		console.warn("Failed to parse SSE JSON payload:", e);
		return;
	}
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/http-stream.js
function ul(e, t = {}) {
	return new dl(e, t).stream;
}
var dl = class {
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
		this.serverUrl = e, this.fetchImpl = fl(t.fetch), this.headers = t.headers ?? {}, this.cookiePolicy = t.cookies ?? "include", this.cookieStore = t.cookieStore ?? new tl(), this.ownsCookieStore = t.cookieStore === void 0, this.stream = {
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
	async postInitialize(e) {
		let t;
		try {
			if (!$c(e)) throw Error("ACP HTTP stream first message must be initialize");
			let n = await this.fetchRequest({
				method: "POST",
				headers: { "Content-Type": Yc },
				body: JSON.stringify(e),
				signal: this.abortController.signal
			});
			if (!n.ok) throw await pl("ACP initialize failed", n);
			let r = n.headers.get(Kc);
			if (!r) throw Error("ACP initialize response missing Acp-Connection-Id");
			t = r, this.throwIfClosedDuringInitialize();
			let i = await n.json();
			if (this.throwIfClosedDuringInitialize(), !m(i)) throw Error("ACP initialize response was not a JSON-RPC response");
			if (el(i.id) !== ("id" in e ? el(e.id) : void 0)) throw Error("ACP initialize response id did not match initialize request");
			this.connectionId = r, this.openConnectionSse(), this.enqueue(i);
		} catch (e) {
			throw this.isClosed && t ? (await this.deleteConnection(t).catch(() => void 0), this.clearOwnedCookieStore()) : this.errorReadable(e, t), e;
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
		let r = n && "method" in e && "id" in e ? el(e.id) : void 0;
		n && r && this.pendingSessionRequests.set(r, n);
		try {
			let r = await this.fetchRequest({
				method: "POST",
				headers: {
					"Content-Type": Yc,
					[Kc]: t,
					...n ? { [qc]: n } : {}
				},
				body: JSON.stringify(e),
				signal: this.abortController.signal
			});
			if (!r.ok) throw await pl("ACP POST failed", r);
			if (!("method" in e) && "id" in e) {
				let t = el(e.id);
				t && this.pendingResponseSessions.delete(t);
			}
		} catch (e) {
			throw r && this.pendingSessionRequests.delete(r), this.errorReadable(e), e;
		}
	}
	sessionIdForOutboundMessage(e) {
		let t = Zc(e);
		if (t) return t;
		if (!("id" in e) || "method" in e) return;
		let n = el(e.id);
		return n ? this.pendingResponseSessions.get(n) : void 0;
	}
	openConnectionSse() {
		let e = this.connectionId;
		e && this.openSse({ [Kc]: e });
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
			[Kc]: n,
			[qc]: e
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
		let n = e[qc];
		try {
			let r = await this.fetchRequest({
				method: "GET",
				headers: {
					Accept: Jc,
					...e
				},
				signal: this.abortController.signal
			});
			if (!r.ok) throw await pl("ACP SSE connection failed", r);
			if (!r.body) throw Error("ACP SSE response missing body");
			t.onOpen?.();
			for await (let t of cl(r.body)) {
				if (this.isClosed) return;
				if (Array.isArray(t)) throw TypeError("ACP HTTP transport does not support JSON-RPC batch messages");
				let n = Qc(t);
				n && this.openSessionSse(n), this.trackServerRequestRoute(t, e[qc]), this.trackInboundResponse(t), this.enqueue(t);
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
		let n = el(e.id);
		n && this.pendingResponseSessions.set(n, t);
	}
	trackInboundResponse(e) {
		if (!m(e)) return;
		let t = el(e.id);
		t && this.pendingSessionRequests.delete(t);
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
			headers: { [Kc]: e }
		});
		if (!t.ok) throw await pl("ACP DELETE failed", t);
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
function fl(e) {
	if (e) return e;
	if (typeof globalThis.fetch == "function") return (e, t) => globalThis.fetch(e, t);
	throw Error("createHttpStream requires globalThis.fetch or options.fetch");
}
async function pl(e, t) {
	let n = await t.text().catch(() => "");
	return Error(n ? `${e}: ${t.status} ${t.statusText}: ${n}` : `${e}: ${t.status} ${t.statusText}`);
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/ws-utils.js
function ml(e, t, n) {
	if (e.on) {
		let r = (...e) => {
			n(...gl(t, e));
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
function hl(e) {
	let t = vl(e);
	if (typeof t == "string") return t;
}
function gl(e, t) {
	return e !== "message" || typeof t[1] != "boolean" ? t : t[1] ? [void 0] : [_l(t[0])];
}
function _l(e) {
	if (typeof e == "string") return e;
	if (e instanceof ArrayBuffer || ArrayBuffer.isView(e)) return new TextDecoder().decode(e);
	if (bl(e)) return xl(e);
}
function vl(e) {
	let [t] = e;
	return yl(t) ? t.data : t;
}
function yl(e) {
	return typeof e == "object" && !!e && "data" in e;
}
function bl(e) {
	return Array.isArray(e) && e.every(ArrayBuffer.isView);
}
function xl(e) {
	let t = e.reduce((e, t) => e + t.byteLength, 0), n = new Uint8Array(t), r = 0;
	for (let t of e) n.set(new Uint8Array(t.buffer, t.byteOffset, t.byteLength), r), r += t.byteLength;
	return new TextDecoder().decode(n);
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/ws-stream.js
var Sl = 1;
function Cl(e, t = {}) {
	return new wl(e, t).stream;
}
var wl = class {
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
		let n = kl(t.WebSocket), r = t.cookies ?? "include";
		this.cookieStore = t.cookieStore ?? new tl(), this.ownsCookieStore = t.cookieStore === void 0, this.socket = new n(e, t.protocols, { headers: Tl(t.headers, r, this.cookieStore) }), this.openPromise = new Promise((e, t) => {
			this.resolveOpen = e, this.rejectOpen = t;
		}), this.openPromise.catch(() => void 0), this.detachListeners.push(ml(this.socket, "open", () => {
			this.resolveOpen?.(), this.resolveOpen = void 0, this.rejectOpen = void 0, this.openPromise = void 0;
		})), this.detachListeners.push(ml(this.socket, "message", (...e) => {
			this.handleSocketMessage(e);
		})), this.detachListeners.push(ml(this.socket, "close", () => {
			this.closeReadable();
		})), this.detachListeners.push(ml(this.socket, "error", (e) => {
			this.errorReadable(e);
		})), r === "include" && this.detachListeners.push(ml(this.socket, "upgrade", (e) => {
			let t = Dl(e);
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
		this.socket.readyState !== void 0 && this.socket.readyState !== Sl && await this.openPromise;
	}
	handleSocketMessage(e) {
		if (this.isClosed) return;
		let t = hl(e);
		if (t === void 0) return;
		let n;
		try {
			n = JSON.parse(t);
		} catch {
			this.sendProtocolError(v.parseError());
			return;
		}
		if (!h(n) && !Array.isArray(n)) {
			this.sendProtocolError(v.invalidRequest(n));
			return;
		}
		this.readableController?.enqueue(n);
	}
	sendProtocolError(e) {
		this.queueMessage(d(e)).catch((e) => {
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
function Tl(e, t, n) {
	let r = e ? { ...e } : {};
	if (t === "include") {
		let t = new Headers(e);
		n.apply(t);
		let i = t.get("Cookie");
		i && (r[El(r, "Cookie") ?? "Cookie"] = i);
	}
	return Object.keys(r).length > 0 ? r : void 0;
}
function El(e, t) {
	return Object.keys(e).find((e) => e.toLowerCase() === t.toLowerCase());
}
function Dl(e) {
	if (e instanceof Headers) return e;
	if (!(!h(e) || !("headers" in e))) return Ol(e.headers);
}
function Ol(e) {
	if (e instanceof Headers) return e;
	if (!h(e)) return;
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
function kl(e) {
	if (e) return e;
	if (typeof globalThis.WebSocket == "function") return globalThis.WebSocket;
	throw Error("createWebSocketStream requires globalThis.WebSocket or options.WebSocket");
}
//#endregion
//#region src/core/transport.ts
function Al(e, t = {}) {
	let n = Ml(e, t.fetch ?? globalThis.fetch), r = fn(t.maxMessageBytes);
	return {
		maxMessageBytes: r,
		open({ signal: i }) {
			return Nl(ul(e, {
				fetch: n,
				...t.headers ? { headers: { ...t.headers } } : {},
				...t.cookies ? { cookies: t.cookies } : {}
			}), i, r);
		}
	};
}
function jl(e, t = {}) {
	let n = fn(t.maxMessageBytes);
	return {
		maxMessageBytes: n,
		open({ signal: r }) {
			return Nl(Cl(e, {
				protocols: [...t.protocols ?? []],
				...t.headers ? { headers: { ...t.headers } } : {},
				...t.cookies ? { cookies: t.cookies } : {},
				...t.WebSocket ? { WebSocket: t.WebSocket } : {}
			}), r, n);
		}
	};
}
function Ml(e, t) {
	if (!t) throw new u("INVALID_CONFIGURATION", "Streamable HTTP requires a fetch implementation", { phase: "transport/http" });
	let n = Pl(e);
	return async (e, r) => {
		let i = Fl(e, n);
		for (let a = 0; a <= 5; a += 1) {
			let o = await t(e, {
				...r,
				redirect: "manual"
			});
			if (o.type === "opaqueredirect") throw new u("INVALID_CONFIGURATION", "ACP HTTP redirects are opaque in browsers; configure a redirect-free endpoint", { phase: "transport/redirect" });
			if (!Il(o.status)) return o;
			let s = o.headers.get("location");
			if (!s) return o;
			let c = new URL(s, i);
			if (c.origin !== n.origin) throw new u("INVALID_CONFIGURATION", `ACP HTTP redirect crossed an origin boundary: ${c.origin}`, { phase: "transport/redirect" });
			if (a === 5) throw new u("INVALID_CONFIGURATION", "ACP HTTP exceeded the redirect limit", { phase: "transport/redirect" });
			e = c.href, i = c;
		}
		throw Error("Unreachable redirect state");
	};
}
function Nl(e, t, n) {
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
				if (!un(i.value, n)) {
					s(new u("PROTOCOL_VIOLATION", `ACP wire message exceeded the ${n} byte decoded input limit`, { phase: "transport/input" }));
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
				if (!un(e, n)) throw new u("PROTOCOL_VIOLATION", `ACP wire message exceeded the ${n} byte decoded output limit`, {
					phase: "transport/output",
					accepted: !1,
					completionUnknown: !1
				});
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
function Pl(e) {
	try {
		return new URL(e, globalThis.location === void 0 ? void 0 : globalThis.location.href);
	} catch (t) {
		throw new u("INVALID_CONFIGURATION", `ACP HTTP endpoint must be an absolute URL: ${e}`, {
			cause: t,
			phase: "transport/http"
		});
	}
}
function Fl(e, t) {
	return typeof e == "string" ? new URL(e, t) : e instanceof URL ? e : new URL(e.url, t);
}
function Il(e) {
	return e >= 300 && e <= 399;
}
//#endregion
//#region src/standalone.tsx
var Ll = 256, Rl = /^[A-Za-z0-9+/_-]+={0,2}$/, zl = /* @__PURE__ */ new WeakMap(), Bl = /* @__PURE__ */ new WeakMap();
function Vl(e, t) {
	if (zl.has(e)) throw Error("pretty-aui: this target is already mounted");
	let n = Object.hasOwn(t, "options");
	if (n === Object.hasOwn(t, "controller")) throw TypeError("pretty-aui: mountChat requires exactly one of options or controller");
	t.styleNonce !== void 0 && Hl(t.styleNonce);
	let r = Bl.get(e);
	if (e.shadowRoot && e.shadowRoot !== r) throw Error("pretty-aui: mountChat requires a target without an existing shadow root");
	let i = r ?? e.attachShadow({ mode: "open" });
	Bl.set(e, i);
	let a = document.createElement("style");
	t.styleNonce !== void 0 && (a.nonce = t.styleNonce), a.textContent = Gc;
	let o = document.createElement("div");
	o.className = "pretty-aui-standalone-root", i.append(a, o);
	let s = {
		shadow: i,
		style: a,
		container: o
	};
	zl.set(e, s);
	let { surface: c, colorScheme: l, labels: u } = t, d = n ? _n(t.options) : t.controller, f = zt(o);
	f.render(/* @__PURE__ */ H(ls, {
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
					zl.get(e) === s && (a.remove(), o.remove(), zl.delete(e));
				}
			}
		}
	};
	return typeof MutationObserver < "u" && (m = Gl(e, () => void h())), {
		controller: d,
		ready: d.ready,
		setDraft(e, t) {
			Ul(p), d.setDraft(e), t?.focus && Wl(i).focus();
		},
		focusComposer() {
			Ul(p), Wl(i).focus();
		},
		unmount: h
	};
}
function Hl(e) {
	if (e.length === 0 || e.length > Ll || !Rl.test(e)) throw TypeError("pretty-aui: styleNonce is not a valid CSP nonce");
}
function Ul(e) {
	if (e) throw Error("pretty-aui: mount has been unmounted");
}
function Wl(e) {
	let t = e.querySelector("[data-pretty-aui-slot=\"composer-input\"] textarea");
	if (!t) throw Error("pretty-aui: composer is not mounted yet");
	return t;
}
function Gl(e, t) {
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
export { u as PrettyAuiError, _n as createChat, Al as createStreamableHttpConnector, jl as createWebSocketConnector, Vl as mountChat };

//# sourceMappingURL=pretty-aui.js.map