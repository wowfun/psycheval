globalThis.__zod_globalConfig ??= {}, globalThis.__zod_globalConfig.jitless = !0;
import { B as e, G as t, H as n, I as r, J as i, K as a, U as o, V as s, W as c, X as l, Y as u, _ as d, a as f, c as p, g as m, h, i as g, l as _, m as v, n as y, o as b, q as x, r as S, s as C, t as w, u as T, z as E } from "./chunks/interactions.js";
//#region node_modules/.pnpm/preact@10.29.8/node_modules/preact/dist/preact.module.js
var D, O, ee, k, te, ne, re, A, ie, j, ae, M, N, oe, se, ce = {}, le = [], ue = /acit|ex(?:s|g|n|p|$)|rph|grid|ows|mnc|ntw|ine[ch]|zoo|^ord|itera/i, de = Array.isArray;
function fe(e, t) {
	for (var n in t) e[n] = t[n];
	return e;
}
function pe(e) {
	e && e.parentNode && e.parentNode.removeChild(e);
}
function me(e, t, n) {
	var r, i, a, o = {};
	for (a in t) a == "key" ? r = t[a] : a == "ref" ? i = t[a] : o[a] = t[a];
	if (arguments.length > 2 && (o.children = arguments.length > 3 ? D.call(arguments, 2) : n), typeof e == "function" && e.defaultProps != null) for (a in e.defaultProps) o[a] === void 0 && (o[a] = e.defaultProps[a]);
	return P(e, o, r, i, null);
}
function P(e, t, n, r, i) {
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
		__v: i ?? ++ee,
		__i: -1,
		__u: 0
	};
	return i == null && O.vnode != null && O.vnode(a), a;
}
function F(e) {
	return e.children;
}
function I(e, t) {
	this.props = e, this.context = t;
}
function he(e, t) {
	if (t == null) return e.__ ? he(e.__, e.__i + 1) : null;
	for (var n; t < e.__k.length; t++) if ((n = e.__k[t]) != null && n.__e != null) return n.__e;
	return typeof e.type == "function" ? he(e) : null;
}
function ge(e) {
	if (e.__P && e.__d) {
		var t = e.__v, n = t.__e, r = [], i = [], a = fe({}, t);
		a.__v = t.__v + 1, O.vnode && O.vnode(a), Oe(e.__P, a, t, e.__n, e.__P.namespaceURI, 32 & t.__u ? [n] : null, r, n ?? he(t), !!(32 & t.__u), i), a.__v = t.__v, a.__.__k[a.__i] = a, Ae(r, a, i), t.__e = t.__ = null, a.__e != n && _e(a);
	}
}
function _e(e) {
	if ((e = e.__) != null && e.__c != null) return e.__e = e.__c.base = null, e.__k.some(function(t) {
		if (t != null && t.__e != null) return e.__e = e.__c.base = t.__e;
	}), _e(e);
}
function ve(e) {
	(!e.__d && (e.__d = !0) && k.push(e) && !ye.__r++ || te != O.debounceRendering) && ((te = O.debounceRendering) || ne)(ye);
}
function ye() {
	try {
		for (var e, t = 1; k.length;) k.length > t && k.sort(re), e = k.shift(), t = k.length, ge(e);
	} finally {
		k.length = ye.__r = 0;
	}
}
function be(e, t, n, r, i, a, o, s, c, l, u) {
	var d, f, p, m, h, g, _ = r && r.__k || le, v = t.length;
	for (c = xe(n, t, _, c, v), d = 0; d < v; d++) (p = n.__k[d]) != null && (f = p.__i != -1 && _[p.__i] || ce, p.__i = d, g = Oe(e, p, f, i, a, o, s, c, l, u), m = p.__e, p.ref && f.ref != p.ref && (f.ref && Ne(f.ref, null, p), u.push(p.ref, p.__c || m, p)), h == null && m != null && (h = m), 4 & p.__u ? (c = Se(p, c, e), f.__e && (f.__e = null)) : typeof p.type == "function" && g !== void 0 ? c = g : m && (c = m.nextSibling), p.__u &= -7);
	return n.__e = h, c;
}
function xe(e, t, n, r, i) {
	var a, o, s, c, l, u = n.length, d = u, f = 0;
	for (e.__k = Array(i), a = 0; a < i; a++) (o = t[a]) != null && typeof o != "boolean" && typeof o != "function" ? (typeof o == "string" || typeof o == "number" || typeof o == "bigint" || o.constructor == String ? o = e.__k[a] = P(null, o, null, null, null) : de(o) ? o = e.__k[a] = P(F, { children: o }, null, null, null) : o.constructor === void 0 && o.__b > 0 ? o = e.__k[a] = P(o.type, o.props, o.key, o.ref ? o.ref : null, o.__v) : e.__k[a] = o, c = a + f, o.__ = e, o.__b = e.__b + 1, s = null, (l = o.__i = we(o, n, c, d)) != -1 && (d--, (s = n[l]) && (s.__u |= 2)), s == null || s.__v == null ? (l == -1 && (i > u ? f-- : i < u && f++), typeof o.type != "function" && (o.__u |= 4)) : l != c && (l == c - 1 ? f-- : l == c + 1 ? f++ : (l > c ? f-- : f++, o.__u |= 4))) : e.__k[a] = null;
	if (d) for (a = 0; a < u; a++) (s = n[a]) != null && !(2 & s.__u) && (s.__e == r && (r = he(s)), Pe(s, s));
	return r;
}
function Se(e, t, n) {
	var r, i;
	if (typeof e.type == "function") {
		for (r = e.__k, i = 0; r && i < r.length; i++) r[i] && (r[i].__ = e, t = Se(r[i], t, n));
		return t;
	}
	e.__e != t && (t && e.type && !t.parentNode && (t = he(e)), t = n.insertBefore(e.__e, t || null));
	do
		t &&= t.nextSibling;
	while (t != null && t.nodeType == 8);
	return t;
}
function Ce(e, t) {
	return t ||= [], e == null || typeof e == "boolean" || (de(e) ? e.some(function(e) {
		Ce(e, t);
	}) : t.push(e)), t;
}
function we(e, t, n, r) {
	var i, a, o, s = e.key, c = e.type, l = t[n], u = l != null && !(2 & l.__u);
	if (l === null && s == null || u && s == l.key && c == l.type) return n;
	if (r > +!!u) {
		for (i = n - 1, a = n + 1; i >= 0 || a < t.length;) if ((l = t[o = i >= 0 ? i-- : a++]) != null && !(2 & l.__u) && s == l.key && c == l.type) return o;
	}
	return -1;
}
function Te(e, t, n) {
	t[0] == "-" ? e.setProperty(t, n ?? "") : e[t] = n == null ? "" : typeof n != "number" || ue.test(t) ? n : n + "px";
}
function Ee(e, t, n, r, i) {
	var a, o;
	n: if (t == "style") {
		if (typeof n == "string") e.style.cssText = n;
		else {
			if (typeof r == "string" && (e.style.cssText = r = ""), r) for (t in r) n && t in n || Te(e.style, t, "");
			if (n) for (t in n) r && n[t] == r[t] || Te(e.style, t, n[t]);
		}
	} else if (t[0] == "o" && t[1] == "n") a = t != (t = t.replace(ae, "$1")), o = t.toLowerCase(), t = o in e || t == "onFocusOut" || t == "onFocusIn" ? o.slice(2) : t.slice(2), e.l ||= {}, e.l[t + a] = n, n ? r ? n[j] = r[j] : (n[j] = M, e.addEventListener(t, a ? oe : N, a)) : e.removeEventListener(t, a ? oe : N, a);
	else {
		if (i == "http://www.w3.org/2000/svg") t = t.replace(/xlink(H|:h)/, "h").replace(/sName$/, "s");
		else if (t != "width" && t != "height" && t != "href" && t != "list" && t != "form" && t != "tabIndex" && t != "download" && t != "rowSpan" && t != "colSpan" && t != "role" && t != "popover" && t in e) try {
			e[t] = n ?? "";
			break n;
		} catch {}
		typeof n == "function" || (n == null || !1 === n && t[4] != "-" ? e.removeAttribute(t) : e.setAttribute(t, t == "popover" && n == 1 ? "" : n));
	}
}
function De(e) {
	return function(t) {
		if (this.l) {
			var n = this.l[t.type + e];
			if (t[ie] == null) t[ie] = M++;
			else if (t[ie] < n[j]) return;
			return n(O.event ? O.event(t) : t);
		}
	};
}
function Oe(e, t, n, r, i, a, o, s, c, l) {
	var u, d, f, p, m, h, g, _, v, y, b, x, S, C, w, T, E = t.type;
	if (t.constructor !== void 0) return null;
	128 & n.__u && (c = !!(32 & n.__u), a = [s = t.__e = n.__e]), (u = O.__b) && u(t);
	n: if (typeof E == "function") {
		d = o.length;
		try {
			if (v = t.props, y = E.prototype && E.prototype.render, b = (u = E.contextType) && r[u.__c], x = u ? b ? b.props.value : u.__ : r, n.__c ? _ = (f = t.__c = n.__c).__ = f.__E : (y ? t.__c = f = new E(v, x) : (t.__c = f = new I(v, x), f.constructor = E, f.render = Fe), b && b.sub(f), f.state || (f.state = {}), f.__n = r, p = f.__d = !0, f.__h = [], f._sb = []), y && f.__s == null && (f.__s = f.state), y && E.getDerivedStateFromProps != null && (f.__s == f.state && (f.__s = fe({}, f.__s)), fe(f.__s, E.getDerivedStateFromProps(v, f.__s))), m = f.props, h = f.state, f.__v = t, p) y && E.getDerivedStateFromProps == null && f.componentWillMount != null && f.componentWillMount(), y && f.componentDidMount != null && f.__h.push(f.componentDidMount);
			else {
				if (y && E.getDerivedStateFromProps == null && v !== m && f.componentWillReceiveProps != null && f.componentWillReceiveProps(v, x), t.__v == n.__v || !f.__e && f.shouldComponentUpdate != null && !1 === f.shouldComponentUpdate(v, f.__s, x)) {
					t.__v != n.__v && (f.props = v, f.state = f.__s, f.__d = !1), t.__e = n.__e, t.__k = n.__k, t.__k.some(function(e) {
						e && (e.__ = t);
					}), le.push.apply(f.__h, f._sb), f._sb = [], f.__h.length && o.push(f), s = he(n);
					break n;
				}
				f.componentWillUpdate != null && f.componentWillUpdate(v, f.__s, x), y && f.componentDidUpdate != null && f.__h.push(function() {
					f.componentDidUpdate(m, h, g);
				});
			}
			if (f.context = x, f.props = v, f.__P = e, f.__e = !1, S = O.__r, C = 0, y) f.state = f.__s, f.__d = !1, S && S(t), u = f.render(f.props, f.state, f.context), le.push.apply(f.__h, f._sb), f._sb = [];
			else do
				f.__d = !1, S && S(t), u = f.render(f.props, f.state, f.context), f.state = f.__s;
			while (f.__d && ++C < 25);
			f.state = f.__s, f.getChildContext != null && (r = fe(fe({}, r), f.getChildContext())), y && !p && f.getSnapshotBeforeUpdate != null && (g = f.getSnapshotBeforeUpdate(m, h)), w = u != null && u.type === F && u.key == null ? je(u.props.children) : u, s = be(e, de(w) ? w : [w], t, n, r, i, a, o, s, c, l), f.base = t.__e, t.__u &= -161, f.__h.length && o.push(f), _ && (f.__E = f.__ = null);
		} catch (e) {
			if (o.length = d, t.__v = null, c || a != null) {
				if (e.then) {
					for (t.__u |= c ? 160 : 128; s && s.nodeType == 8 && s.nextSibling;) s = s.nextSibling;
					a != null && (a[a.indexOf(s)] = null), t.__e = s;
				} else if (a != null) for (T = a.length; T--;) pe(a[T]);
			} else t.__e = n.__e;
			t.__k ??= n.__k || [], e.then || ke(t), O.__e(e, t, n);
		}
	} else a == null && t.__v == n.__v ? (t.__k = n.__k, t.__e = n.__e) : s = t.__e = Me(n.__e, t, n, r, i, a, o, c, l);
	return (u = O.diffed) && u(t), 128 & t.__u ? void 0 : s;
}
function ke(e) {
	e && (e.__c && (e.__c.__e = !0), e.__k && e.__k.some(ke));
}
function Ae(e, t, n) {
	for (var r = 0; r < n.length; r++) Ne(n[r], n[++r], n[++r]);
	O.__c && O.__c(t, e), e.some(function(t) {
		try {
			e = t.__h, t.__h = [], e.some(function(e) {
				e.call(t);
			});
		} catch (e) {
			O.__e(e, t.__v);
		}
	});
}
function je(e) {
	return typeof e != "object" || !e || e.__b > 0 ? e : de(e) ? e.map(je) : e.constructor === void 0 ? fe({}, e) : null;
}
function Me(e, t, n, r, i, a, o, s, c) {
	var l, u, d, f, p, m, h, g = n.props || ce, _ = t.props, v = t.type;
	if (v == "svg" ? i = "http://www.w3.org/2000/svg" : v == "math" ? i = "http://www.w3.org/1998/Math/MathML" : i ||= "http://www.w3.org/1999/xhtml", a != null) {
		for (l = 0; l < a.length; l++) if ((p = a[l]) && "setAttribute" in p == !!v && (v ? p.localName == v : p.nodeType == 3)) {
			e = p, a[l] = null;
			break;
		}
	}
	if (e == null) {
		if (v == null) return document.createTextNode(_);
		e = document.createElementNS(i, v, _.is && _), s &&= (O.__m && O.__m(t, a), !1), a = null;
	}
	if (v == null) g === _ || s && e.data == _ || (e.data = _);
	else {
		if (a = v == "textarea" && _.defaultValue != null ? null : a && D.call(e.childNodes), !s && a != null) for (g = {}, l = 0; l < e.attributes.length; l++) g[(p = e.attributes[l]).name] = p.value;
		for (l in g) p = g[l], l == "dangerouslySetInnerHTML" ? d = p : l == "children" || l in _ || l == "value" && "defaultValue" in _ || l == "checked" && "defaultChecked" in _ || Ee(e, l, null, p, i);
		for (l in _) p = _[l], l == "children" ? f = p : l == "dangerouslySetInnerHTML" ? u = p : l == "value" ? m = p : l == "checked" ? h = p : s && typeof p != "function" || g[l] === p || Ee(e, l, p, g[l], i);
		if (u) s || d && (u.__html == d.__html || u.__html == e.innerHTML) || (e.innerHTML = u.__html), t.__k = [];
		else if (d && (e.innerHTML = ""), be(t.type == "template" ? e.content : e, de(f) ? f : [f], t, n, r, v == "foreignObject" ? "http://www.w3.org/1999/xhtml" : i, a, o, a ? a[0] : n.__k && he(n, 0), s, c), a != null) for (l = a.length; l--;) pe(a[l]);
		s && v != "textarea" || (l = "value", v == "progress" && m == null ? e.removeAttribute("value") : m != null && (m !== e[l] || v == "progress" && !m || v == "option" && m != g[l]) && Ee(e, l, m, g[l], i), l = "checked", h != null && h != e[l] && Ee(e, l, h, g[l], i));
	}
	return e;
}
function Ne(e, t, n) {
	try {
		if (typeof e == "function") {
			var r = typeof e.__u == "function";
			r && e.__u(), r && t == null || (e.__u = e(t));
		} else e.current = t;
	} catch (e) {
		O.__e(e, n);
	}
}
function Pe(e, t, n) {
	var r, i;
	if (O.unmount && O.unmount(e), (r = e.ref) && (r.current && r.current != e.__e || Ne(r, null, t)), (r = e.__c) != null) {
		if (r.componentWillUnmount) try {
			r.componentWillUnmount();
		} catch (e) {
			O.__e(e, t);
		}
		r.base = r.__P = r.__n = null;
	}
	if (r = e.__k) for (i = 0; i < r.length; i++) r[i] && Pe(r[i], t, n || typeof e.type != "function");
	n || pe(e.__e), e.__c = e.__ = e.__e = void 0;
}
function Fe(e, t, n) {
	return this.constructor(e, n);
}
function Ie(e, t, n) {
	var r, i, a, o;
	t == document && (t = document.documentElement), O.__ && O.__(e, t), i = (r = typeof n == "function") ? null : n && n.__k || t.__k, a = [], o = [], Oe(t, e = (!r && n || t).__k = me(F, null, [e]), i || ce, ce, t.namespaceURI, !r && n ? [n] : i ? null : t.firstChild ? D.call(t.childNodes) : null, a, !r && n ? n : i ? i.__e : t.firstChild, r, o), Ae(a, e, o), e.props.children = null;
}
function Le(e) {
	function t(e) {
		var n, r;
		return this.getChildContext || (n = /* @__PURE__ */ new Set(), (r = {})[t.__c] = this, this.getChildContext = function() {
			return r;
		}, this.componentWillUnmount = function() {
			n = null;
		}, this.shouldComponentUpdate = function(e) {
			this.props.value != e.value && n.forEach(function(e) {
				e.__e = !0, ve(e);
			});
		}, this.sub = function(e) {
			n.add(e);
			var t = e.componentWillUnmount;
			e.componentWillUnmount = function() {
				n && n.delete(e), t && t.call(e);
			};
		}), e.children;
	}
	return t.__c = "__cC" + se++, t.__ = e, t.Provider = t.__l = (t.Consumer = function(e, t) {
		return e.children(t);
	}).contextType = t, t;
}
D = le.slice, O = { __e: function(e, t, n, r) {
	for (var i, a, o; t = t.__;) if ((i = t.__c) && !i.__) try {
		if ((a = i.constructor) && a.getDerivedStateFromError != null && (i.setState(a.getDerivedStateFromError(e)), o = i.__d), i.componentDidCatch != null && (i.componentDidCatch(e, r || {}), o = i.__d), o) return i.__E = i;
	} catch (t) {
		e = t;
	}
	throw e;
} }, ee = 0, I.prototype.setState = function(e, t) {
	var n = this.__s != null && this.__s != this.state ? this.__s : this.__s = fe({}, this.state);
	typeof e == "function" && (e = e(fe({}, n), this.props)), e && fe(n, e), e != null && this.__v && (t && this._sb.push(t), ve(this));
}, I.prototype.forceUpdate = function(e) {
	this.__v && (this.__e = !0, e && this.__h.push(e), ve(this));
}, I.prototype.render = F, k = [], ne = typeof Promise == "function" ? Promise.prototype.then.bind(Promise.resolve()) : setTimeout, re = function(e, t) {
	return e.__v.__b - t.__v.__b;
}, ye.__r = 0, A = Math.random().toString(8), ie = "__d" + A, j = "__a" + A, ae = /(PointerCapture)$|Capture$/i, M = 0, N = De(!1), oe = De(!0), se = 0;
//#endregion
//#region node_modules/.pnpm/preact@10.29.8/node_modules/preact/hooks/dist/hooks.module.js
var Re, L, ze, Be, Ve = 0, He = [], R = O, Ue = R.__b, We = R.__r, Ge = R.diffed, Ke = R.__c, qe = R.unmount, Je = R.__;
function Ye(e, t) {
	R.__h && R.__h(L, e, Ve || t), Ve = 0;
	var n = L.__H || (L.__H = {
		__: [],
		__h: []
	});
	return e >= n.__.length && n.__.push({}), n.__[e];
}
function z(e) {
	return Ve = 1, Xe(st, e);
}
function Xe(e, t, n) {
	var r = Ye(Re++, 2);
	if (r.t = e, !r.__c && (r.__ = [n ? n(t) : st(void 0, t), function(e) {
		var t = r.__N ? r.__N[0] : r.__[0], n = r.t(t, e);
		t !== n && (r.__N = [n, r.__[1]], r.__c.setState({}));
	}], r.__c = L, !L.__f)) {
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
		L.__f = !0;
		var a = L.shouldComponentUpdate, o = L.componentWillUpdate;
		L.componentWillUpdate = function(e, t, n) {
			if (this.__e) {
				var r = a;
				a = void 0, i(e, t, n), a = r;
			}
			o && o.call(this, e, t, n);
		}, L.shouldComponentUpdate = i;
	}
	return r.__N || r.__;
}
function B(e, t) {
	var n = Ye(Re++, 3);
	!R.__s && ot(n.__H, t) && (n.__ = e, n.u = t, L.__H.__h.push(n));
}
function Ze(e, t) {
	var n = Ye(Re++, 4);
	!R.__s && ot(n.__H, t) && (n.__ = e, n.u = t, L.__h.push(n));
}
function V(e) {
	return Ve = 5, Qe(function() {
		return { current: e };
	}, []);
}
function Qe(e, t) {
	var n = Ye(Re++, 7);
	return ot(n.__H, t) && (n.__ = e(), n.__H = t, n.__h = e), n.__;
}
function $e(e, t) {
	return Ve = 8, Qe(function() {
		return e;
	}, t);
}
function et(e) {
	var t = L.context[e.__c], n = Ye(Re++, 9);
	return n.c = e, t ? (n.__ ?? (n.__ = !0, t.sub(L)), t.props.value) : e.__;
}
function H() {
	var e = Ye(Re++, 11);
	if (!e.__) {
		for (var t = L.__v; t !== null && !t.__m && t.__ !== null;) t = t.__;
		var n = t.__m || (t.__m = [0, 0]);
		e.__ = "P" + n[0] + "-" + n[1]++;
	}
	return e.__;
}
function tt() {
	for (var e; e = He.shift();) {
		var t = e.__H;
		if (e.__P && t) try {
			t.__h.some(it), t.__h.some(at), t.__h = [];
		} catch (n) {
			t.__h = [], R.__e(n, e.__v);
		}
	}
}
R.__b = function(e) {
	L = null, Ue && Ue(e);
}, R.__ = function(e, t) {
	e && t.__k && t.__k.__m && (e.__m = t.__k.__m), Je && Je(e, t);
}, R.__r = function(e) {
	We && We(e), Re = 0;
	var t = (L = e.__c).__H;
	t && (ze === L ? (t.__h = [], L.__h = [], t.__.some(function(e) {
		e.__N && (e.__ = e.__N), e.u = e.__N = void 0;
	})) : (t.__h.some(it), t.__h.some(at), t.__h = [], Re = 0)), ze = L;
}, R.diffed = function(e) {
	Ge && Ge(e);
	var t = e.__c;
	t && t.__H && (t.__H.__h.length && (He.push(t) !== 1 && Be === R.requestAnimationFrame || ((Be = R.requestAnimationFrame) || rt)(tt)), t.__H.__.some(function(e) {
		e.u &&= (e.__H = e.u, void 0);
	})), ze = L = null;
}, R.__c = function(e, t) {
	t.some(function(e) {
		try {
			e.__h.some(it), e.__h = e.__h.filter(function(e) {
				return !e.__ || at(e);
			});
		} catch (n) {
			t.some(function(e) {
				e.__h &&= [];
			}), t = [], R.__e(n, e.__v);
		}
	}), Ke && Ke(e, t);
}, R.unmount = function(e) {
	qe && qe(e);
	var t, n = e.__c;
	n && n.__H && (n.__H.__.some(function(e) {
		try {
			it(e);
		} catch (e) {
			t = e;
		}
	}), n.__H = void 0, t && R.__e(t, n.__v));
};
var nt = typeof requestAnimationFrame == "function";
function rt(e) {
	var t, n = function() {
		clearTimeout(r), nt && cancelAnimationFrame(t), setTimeout(e);
	}, r = setTimeout(n, 35);
	nt && (t = requestAnimationFrame(n));
}
function it(e) {
	var t = L, n = e.__c;
	typeof n == "function" && (e.__c = void 0, n()), L = t;
}
function at(e) {
	var t = L;
	e.__c = e.__(), L = t;
}
function ot(e, t) {
	return !e || e.length !== t.length || t.some(function(t, n) {
		return t !== e[n];
	});
}
function st(e, t) {
	return typeof t == "function" ? t(e) : t;
}
//#endregion
//#region node_modules/.pnpm/preact@10.29.8/node_modules/preact/compat/dist/compat.module.js
function ct(e, t) {
	for (var n in t) e[n] = t[n];
	return e;
}
function lt(e, t) {
	for (var n in e) if (n !== "__source" && !(n in t)) return !0;
	for (var r in t) if (r !== "__source" && e[r] !== t[r]) return !0;
	return !1;
}
function ut(e, t) {
	var n = t(), r = z({ t: {
		__: n,
		u: t
	} }), i = r[0].t, a = r[1];
	return Ze(function() {
		i.__ = n, i.u = t, dt(i) && a({ t: i });
	}, [
		e,
		n,
		t
	]), B(function() {
		return dt(i) && a({ t: i }), e(function() {
			dt(i) && a({ t: i });
		});
	}, [e]), n;
}
function dt(e) {
	try {
		return !((t = e.__) === (n = e.u()) && (t !== 0 || 1 / t == 1 / n) || t != t && n != n);
	} catch {
		return !0;
	}
	var t, n;
}
function ft(e, t) {
	this.props = e, this.context = t;
}
function pt(e, t) {
	function n(e) {
		var n = this.props.ref;
		return n != e.ref && n && (typeof n == "function" ? n(null) : n.current = null), t ? !t(this.props, e) || n != e.ref : lt(this.props, e);
	}
	function r(t) {
		return this.shouldComponentUpdate = n, me(e, t);
	}
	return r.displayName = "Memo(" + (e.displayName || e.name) + ")", r.__f = r.prototype.isReactComponent = !0, r.type = e, r;
}
(ft.prototype = new I()).isPureReactComponent = !0, ft.prototype.shouldComponentUpdate = function(e, t) {
	return lt(this.props, e) || lt(this.state, t);
};
var mt = O.__b;
O.__b = function(e) {
	e.type && e.type.__f && e.ref && (e.props.ref = e.ref, e.ref = null), mt && mt(e);
}, typeof Symbol < "u" && Symbol.for;
var ht = O.__e;
O.__e = function(e, t, n, r) {
	if (e.then) {
		for (var i, a = t; a = a.__;) if ((i = a.__c) && i.__c) return t.__e ?? (t.__e = n.__e, t.__k = n.__k || []), i.__c(e, t);
	}
	ht(e, t, n, r);
};
var gt = O.unmount;
function _t(e, t, n) {
	return e && (e.__c && e.__c.__H && (e.__c.__H.__.forEach(function(e) {
		typeof e.__c == "function" && e.__c();
	}), e.__c.__H = null), (e = ct({}, e)).__c != null && (e.__c.__P === n && (e.__c.__P = t), e.__c.__e = !0, e.__c = null), e.__k = e.__k && e.__k.map(function(e) {
		return _t(e, t, n);
	})), e;
}
function vt(e, t, n) {
	return e && n && (e.__v = null, e.__k = e.__k && e.__k.map(function(e) {
		return vt(e, t, n);
	}), e.__c && e.__c.__P === t && (e.__e && n.appendChild(e.__e), e.__c.__e = !0, e.__c.__P = n)), e;
}
function yt() {
	this.__u = 0, this.o = null, this.__b = null;
}
function bt(e) {
	var t = e.__ && e.__.__c;
	return t && t.__a && t.__a(e);
}
function xt() {
	this.i = null, this.l = null;
}
O.unmount = function(e) {
	var t = e.__c;
	t && (t.__z = !0), t && t.__R && t.__R(), t && 32 & e.__u && (e.type = null), gt && gt(e);
}, (yt.prototype = new I()).__c = function(e, t) {
	var n = t.__c, r = this;
	r.o ??= [], r.o.push(n);
	var i = bt(r.__v), a = !1, o = function() {
		a || r.__z || (a = !0, n.__R = null, i ? i(c) : c());
	};
	n.__R = o;
	var s = n.__P;
	n.__P = null;
	var c = function() {
		if (!--r.__u) {
			if (r.state.__a) {
				var e = r.state.__a;
				r.__v.__k[0] = vt(e, e.__c.__P, e.__c.__O);
			}
			var t;
			for (r.setState({ __a: r.__b = null }); t = r.o.pop();) t.__P = s, t.forceUpdate();
		}
	};
	r.__u++ || 32 & t.__u || r.setState({ __a: r.__b = r.__v.__k[0] }), e.then(o, o);
}, yt.prototype.componentWillUnmount = function() {
	this.o = [];
}, yt.prototype.render = function(e, t) {
	if (this.__b) {
		if (this.__v.__k) {
			var n = document.createElement("div"), r = this.__v.__k[0].__c;
			this.__v.__k[0] = _t(this.__b, n, r.__O = r.__P);
		}
		this.__b = null;
	}
	var i = t.__a && me(F, null, e.fallback);
	return i && (i.__u &= -33), [me(F, null, t.__a ? null : e.children), i];
};
var St = function(e, t, n) {
	if (++n[1] === n[0] && e.l.delete(t), e.props.revealOrder && (e.props.revealOrder[0] !== "t" || !e.l.size)) for (n = e.i; n;) {
		for (; n.length > 3;) n.pop()();
		if (n[1] < n[0]) break;
		e.i = n = n[2];
	}
};
(xt.prototype = new I()).__a = function(e) {
	var t = this, n = bt(t.__v), r = t.l.get(e);
	return r[0]++, function(i) {
		var a = function() {
			t.props.revealOrder ? (r.push(i), St(t, e, r)) : i();
		};
		n ? n(a) : a();
	};
}, xt.prototype.render = function(e) {
	this.i = null, this.l = /* @__PURE__ */ new Map();
	var t = Ce(e.children);
	e.revealOrder && e.revealOrder[0] === "b" && t.reverse();
	for (var n = t.length; n--;) this.l.set(t[n], this.i = [
		1,
		0,
		this.i
	]);
	return e.children;
}, xt.prototype.componentDidUpdate = xt.prototype.componentDidMount = function() {
	var e = this;
	this.l.forEach(function(t, n) {
		St(e, n, t);
	});
};
var Ct = typeof Symbol < "u" && Symbol.for && Symbol.for("react.element") || 60103, wt = /^(?:accent|alignment|arabic|baseline|cap|clip(?!PathU)|color|dominant|fill|flood|font|glyph(?!R)|horiz|image(!S)|letter|lighting|marker(?!H|W|U)|overline|paint|pointer|shape|stop|strikethrough|stroke|text(?!L)|transform|underline|unicode|units|v|vector|vert|word|writing|x(?!C))[A-Z]/, Tt = /^on(Ani|Tra|Tou|BeforeInp|Compo)/, Et = /[A-Z0-9]/g, Dt = typeof document < "u", Ot = function(e) {
	return (typeof Symbol < "u" && typeof Symbol() == "symbol" ? /fil|che|rad/ : /fil|che|ra/).test(e);
};
function kt(e, t, n) {
	return t.__k ?? (t.textContent = ""), Ie(e, t), typeof n == "function" && n(), e ? e.__c : null;
}
I.prototype.isReactComponent = !0, [
	"componentWillMount",
	"componentWillReceiveProps",
	"componentWillUpdate"
].forEach(function(e) {
	Object.defineProperty(I.prototype, e, {
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
var At = O.event;
O.event = function(e) {
	return At && (e = At(e)), e.persist = function() {}, e.isPropagationStopped = function() {
		return this.cancelBubble;
	}, e.isDefaultPrevented = function() {
		return this.defaultPrevented;
	}, e.nativeEvent = e;
};
var jt = {
	configurable: !0,
	get: function() {
		return this.class;
	}
}, Mt = O.vnode;
O.vnode = function(e) {
	typeof e.type == "string" && function(e) {
		var t = e.props, n = e.type, r = {}, i = n.indexOf("-") == -1;
		for (var a in t) {
			var o = t[a];
			if (!(a === "value" && "defaultValue" in t && o == null || Dt && a === "children" && n === "noscript" || a === "class" || a === "className")) {
				var s = a.toLowerCase();
				a === "defaultValue" && "value" in t && t.value == null ? a = "value" : a === "download" && !0 === o ? o = "" : s === "translate" && o === "no" ? o = !1 : s[0] === "o" && s[1] === "n" ? s === "ondoubleclick" ? a = "ondblclick" : s !== "onchange" || n !== "input" && n !== "textarea" || Ot(t.type) ? s === "onfocus" ? a = "onfocusin" : s === "onblur" ? a = "onfocusout" : Tt.test(a) && (a = s) : s = a = "oninput" : i && wt.test(a) ? a = a.replace(Et, "-$&").toLowerCase() : o === null && (o = void 0), s === "oninput" && r[a = s] && (a = "oninputCapture"), r[a] = o;
			}
		}
		n == "select" && (r.multiple && Array.isArray(r.value) && (r.value = Ce(t.children).forEach(function(e) {
			e.props.selected = r.value.indexOf(e.props.value) != -1;
		})), r.defaultValue != null && (r.value = Ce(t.children).forEach(function(e) {
			e.props.selected = r.multiple ? r.defaultValue.indexOf(e.props.value) != -1 : r.defaultValue == e.props.value;
		}))), t.class && !t.className ? (r.class = t.class, Object.defineProperty(r, "className", jt)) : t.className && (r.class = r.className = t.className), e.props = r;
	}(e), e.$$typeof = Ct, Mt && Mt(e);
};
var Nt = O.__r;
O.__r = function(e) {
	Nt && Nt(e), e.__c;
};
var Pt = O.diffed;
O.diffed = function(e) {
	Pt && Pt(e);
	var t = e.props, n = e.__e;
	n != null && e.type === "textarea" && "value" in t && t.value !== n.value && (n.value = t.value == null ? "" : t.value);
};
function Ft(e) {
	return !!e.__k && (Ie(null, e), !0);
}
//#endregion
//#region node_modules/.pnpm/preact@10.29.8/node_modules/preact/compat/client.mjs
function It(e) {
	return {
		render: function(t) {
			kt(t, e);
		},
		unmount: function() {
			Ft(e);
		}
	};
}
var Lt = {
	name: "pretty-aui",
	version: "0.1.0-rc.1",
	description: "Composable Agent Client Protocol (ACP) chat UI for React and static sites, with a standalone Shadow DOM bundle.",
	repository: {
		type: "git",
		url: "git+https://github.com/wowfun/pretty-aui.git"
	},
	homepage: "https://github.com/wowfun/pretty-aui#readme",
	bugs: { url: "https://github.com/wowfun/pretty-aui/issues" },
	keywords: [
		"agent-client-protocol",
		"acp",
		"chat-ui",
		"react",
		"shadow-dom",
		"static-site",
		"typescript",
		"opencode"
	],
	type: "module",
	license: "MIT",
	sideEffects: ["**/*.css"],
	files: [
		"bin/pretty-aui.mjs",
		"dist",
		"docs",
		"src",
		"README.md",
		"README.zh-CN.md",
		"LICENSE"
	],
	main: "./dist/index.js",
	module: "./dist/index.js",
	types: "./dist/index.d.ts",
	exports: {
		".": {
			types: "./dist/index.d.ts",
			import: "./dist/index.js"
		},
		"./core": {
			types: "./dist/core/index.d.ts",
			import: "./dist/core/index.js"
		},
		"./react": {
			types: "./dist/react/index.d.ts",
			import: "./dist/react/index.js"
		},
		"./standalone": {
			types: "./dist/standalone.d.ts",
			import: "./dist/standalone/pretty-aui.js"
		},
		"./styles.css": {
			types: "./dist/styles.css.d.ts",
			default: "./dist/styles.css"
		},
		"./package.json": "./package.json"
	},
	scripts: {
		dev: "vite --config examples/react/vite.config.ts",
		"dev:opencode": "node scripts/dev-opencode.mjs",
		build: "node scripts/clean.mjs && tsc -p tsconfig.esm.json && tsc -p tsconfig.build.json && vite build && node scripts/copy-assets.mjs",
		format: "prettier --write .",
		check: "pnpm check:format && pnpm check:types && pnpm test && pnpm check:docs && pnpm check:package",
		"check:dist": "node scripts/check-package.mjs",
		"check:docs": "node scripts/check-docs.mjs",
		"check:format": "prettier --check .",
		"check:package": "pnpm build && node -e \"require('node:fs').mkdirSync('.local/package', { recursive: true })\" && npm pack --ignore-scripts --pack-destination .local/package --silent && node scripts/check-package.mjs",
		"check:types": "tsc -p tsconfig.json --noEmit",
		test: "vitest run",
		"test:coverage": "vitest run --coverage",
		"test:watch": "vitest",
		"test:e2e": "node scripts/test-e2e.mjs --project=chromium",
		"test:e2e:compat": "node scripts/test-e2e.mjs --project=firefox --project=webkit",
		"test:opencode": "pnpm build && node scripts/live-opencode.mjs",
		prepack: "pnpm build",
		"example:jekyll": "pnpm build && node bin/pretty-aui.mjs vendor examples/jekyll/assets/vendor"
	},
	dependencies: {
		"@agentclientprotocol/sdk": "1.4.0",
		dompurify: "^3.4.14",
		"isomorphic-dompurify": "3.23.0",
		marked: "^18.0.10",
		zod: "^4.4.3"
	},
	peerDependencies: {
		react: "^18.3.0 || ^19.0.0",
		"react-dom": "^18.3.0 || ^19.0.0"
	},
	peerDependenciesMeta: {
		react: { optional: !0 },
		"react-dom": { optional: !0 }
	},
	devDependencies: {
		"@arethetypeswrong/cli": "^0.18.2",
		"@playwright/test": "^1.62.1",
		"@testing-library/dom": "^10.4.1",
		"@testing-library/jest-dom": "6.9.1",
		"@testing-library/react": "^16.3.2",
		"@types/node": "^26.3.0",
		"@types/react": "^18.3.0",
		"@types/react-dom": "^18.3.0",
		"@types/ws": "^8.18.1",
		"@vitejs/plugin-react": "^6.0.1",
		"@vitest/coverage-v8": "4.1.11",
		jsdom: "^27.4.0",
		preact: "^10.29.8",
		prettier: "^3.9.0",
		publint: "^0.3.24",
		react: "^19.2.8",
		"react-dom": "^19.2.8",
		typescript: "7.0.2",
		vite: "^8.2.2",
		vitest: "^4.1.11",
		ws: "^8.19.0"
	},
	engines: { node: "^22.22.2 || ^24.15.0 || >=26.0.0" },
	packageManager: "pnpm@10.34.0",
	bin: { "pretty-aui": "bin/pretty-aui.mjs" },
	publishConfig: {
		access: "public",
		tag: "rc"
	}
}, Rt = 8388608, zt = Object.freeze({
	text: "",
	images: Object.freeze([]),
	revision: 0,
	locked: !1,
	recoverable: Object.freeze([])
});
function Bt(e, t) {
	return t ? e ? `${e}\n\n${t}` : t : e;
}
function Vt(e, t, n) {
	if (!n.some((e) => e.name === t)) throw Gt("Unknown Agent command");
	let r = /^\/([^\s]+)(\s|$)/.exec(e);
	return `/${t} ${r && n.some((e) => e.name === r[1]) ? e.slice(r[0].length) : e}`;
}
function Ht(e) {
	return e.reduce((e, t) => e + t.data.length, 0);
}
function Ut(e, t) {
	if (e.length > 1048576) throw Gt("Draft text exceeds 1 MiB");
	if (t.length > 4 || Ht(t) > 8388608) throw Gt("A message allows four images and 8 MiB of base64 data");
	let n = /* @__PURE__ */ new Set();
	for (let e of t) {
		if (!e.id || n.has(e.id) || e.type !== "image" || !/^image\/(png|jpeg|webp|gif)$/.test(e.mimeType) || !e.data || e.data.length > 8388608 || e.data.length % 4 || !/^[A-Za-z0-9+/]*={0,2}$/.test(e.data)) throw Gt("Invalid draft image");
		n.add(e.id);
	}
}
var Wt = class {
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = new WeakSet([zt.images]);
	#r(e) {
		if (this.#n.has(e)) return e;
		let t = Object.freeze(e.map((e) => Object.freeze({ ...e })));
		return Ut("", t), this.#n.add(t), t;
	}
	get(e) {
		return this.#e.get(e) ?? zt;
	}
	set(e, t, n = this.get(e).images) {
		let r = this.get(e);
		if (r.locked) throw Gt("Wait for local submission preparation");
		this.#i(e, {
			...r,
			text: t,
			images: n,
			revision: r.revision + 1
		});
	}
	#i(e, t) {
		if (t.text.length > 1048576) throw Gt("Draft text exceeds 1 MiB");
		t = {
			...t,
			images: this.#r(t.images)
		};
		let n = Ht(t.images) + t.recoverable.reduce((e, t) => e + Ht(t.images), 0);
		for (let [t, r] of this.#e) t !== e && (n += Ht(r.images) + r.recoverable.reduce((e, t) => e + Ht(t.images), 0));
		for (let e of this.#t.values()) n += Ht(e.images);
		if (n > 33554432) throw Gt("Pending and recoverable images exceed 32 MiB");
		this.#e.set(e, Object.freeze(t));
	}
	lock(e) {
		let t = this.get(e);
		if (this.#t.has(e)) throw Gt("A submission is already in flight");
		if (t.locked) throw Gt("A draft is already being prepared");
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
		if (!t.locked || this.#t.has(e)) throw Gt("No prepared submission is available");
		this.#t.set(e, {
			id: `${e}:${t.revision}`,
			text: t.text,
			images: t.images
		}), this.#e.set(e, {
			...t,
			text: "",
			images: zt.images,
			locked: !1,
			revision: t.revision + 1
		});
	}
	failed(e, t) {
		let n = this.#t.get(e);
		if (n && n.id !== t.id) throw Gt("Stale submission failure");
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
		if (n.locked) throw Gt("Wait for local submission preparation");
		let r = n.recoverable.find((e) => e.id === t);
		if (!r) throw Gt("Failed submission is unavailable");
		this.#i(e, {
			...n,
			text: Bt(n.text, r.text),
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
function Gt(e) {
	return new u("INVALID_CONFIGURATION", e, { phase: "composer" });
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/line-buffer.js
var Kt = 10, qt = class {
	#e = [];
	push(e) {
		let t = [], n = 0, r = e.indexOf(Kt, n);
		for (; r !== -1;) t.push(this.#t(e.subarray(n, r))), n = r + 1, r = e.indexOf(Kt, n);
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
async function Jt(e) {
	let { sink: t, host: n } = e, r = _({ name: e.clientInfo.name });
	r = r.onRequest(T.client.session.requestPermission, async ({ params: e }) => {
		let n = e, r = await t.onPermission(e.sessionId, $t(n), n);
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
	let d = l.agentCapabilities, f = d?.sessionCapabilities, p = new Yt(s, {
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
var Yt = class {
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
		let t = await b(() => this.connection.agent.request(T.agent.session.new, Xt(e)), 1, "session/new");
		return this.#e.set(t.sessionId, !t.configOptions?.length && !!t.modes), Qt(t.sessionId, t.configOptions, t.modes);
	}
	async openSession(e, t, n) {
		p(t, this.initialized, 1, "session/open");
		let r = {
			...Xt(t),
			sessionId: e
		};
		if (n === "all" && this.initialized.capabilities.loadSession) {
			let t = await b(() => this.connection.agent.request(T.agent.session.load, r), 1, "session/open");
			return this.#e.set(e, !t.configOptions?.length && !!t.modes), Qt(e, t.configOptions, t.modes);
		}
		if (!this.initialized.capabilities.resumeSession) throw new u("CAPABILITY_REQUIRED", "The agent cannot open existing sessions", {
			protocol: 1,
			phase: "session/resume"
		});
		let i = await b(() => this.connection.agent.request(T.agent.session.resume, r), 1, "session/open");
		return this.#e.set(e, !i.configOptions?.length && !!i.modes), Qt(e, i.configOptions, i.modes, n === "all");
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
function Xt(e) {
	return {
		cwd: e.cwd,
		mcpServers: (e.mcpServers ?? []).map(Zt),
		...e.additionalDirectories?.length ? { additionalDirectories: [...e.additionalDirectories] } : {}
	};
}
function Zt(e) {
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
function Qt(e, n, r, i = !1) {
	let a = c(n);
	return {
		sessionId: e,
		configOptions: a.length ? a : t(r),
		...i ? { historyGap: i } : {}
	};
}
function $t(t) {
	let r = n(t) ? t : {}, i = n(r.toolCall) ? r.toolCall : {};
	return {
		type: "permission",
		title: e(i.title) ?? "Permission required",
		options: S(r.options)
	};
}
//#endregion
//#region src/core/protocol/connect.ts
async function en(e) {
	if (e.protocol === 1) return tn(1, 1, e);
	if (e.protocol === 2) return tn(2, 1, e);
	let t = await e.connector.open({
		protocol: 2,
		attempt: 1,
		signal: e.signal
	}), n = rn(t);
	try {
		return await nn(n.stream, e);
	} catch (r) {
		if (n.negotiatedVersion() !== 1) throw r;
		return await sn(t), tn(1, 2, e);
	}
}
async function tn(e, t, n) {
	let r = await n.connector.open({
		protocol: e,
		attempt: t,
		signal: n.signal
	});
	if (n.signal.aborted) throw await sn(r), new u("CONNECTION_CLOSED", "Connection was cancelled", {
		protocol: e,
		retryable: !0
	});
	return e === 1 ? Jt({
		stream: r,
		sink: n.sink,
		clientInfo: n.clientInfo,
		...n.host ? { host: n.host } : {}
	}) : nn(r, n);
}
async function nn(e, t) {
	let { connectV2: n } = await import("./chunks/v2.js");
	return n({
		stream: e,
		sink: t.sink,
		clientInfo: t.clientInfo,
		...t.host ? { host: t.host } : {}
	});
}
function rn(e) {
	let t, n, r = e.writable, i = e.readable, a = new WritableStream({
		async write(e) {
			let n = an(e);
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
				for (let e of i) !on(e) || e.id !== t || !on(e.result) || typeof e.result.protocolVersion == "number" && (n = e.result.protocolVersion);
				r.enqueue(e);
			} })),
			writable: a
		},
		negotiatedVersion: () => n
	};
}
function an(e) {
	let t = Array.isArray(e) ? e : [e];
	for (let e of t) if (on(e) && e.method === "initialize" && Object.hasOwn(e, "id")) return { id: e.id };
}
function on(e) {
	return typeof e == "object" && !!e && !Array.isArray(e);
}
async function sn(e) {
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
var cn = 2097152;
function ln(e, t = cn) {
	let n;
	try {
		n = JSON.stringify(e);
	} catch {
		return !1;
	}
	return n !== void 0 && un(n, t);
}
function un(e, t) {
	let n = 0;
	for (let r = 0; r < e.length; r += 1) {
		let i = e.charCodeAt(r);
		if (i <= 127 ? n += 1 : i <= 2047 ? n += 2 : i >= 55296 && i <= 56319 && r + 1 < e.length && e.charCodeAt(r + 1) >= 56320 && e.charCodeAt(r + 1) <= 57343 ? (n += 4, r += 1) : n += 3, n > t) return !1;
	}
	return !0;
}
function dn(e) {
	if (e === void 0) return cn;
	if (!Number.isSafeInteger(e) || e <= 0) throw RangeError("maxMessageBytes must be a positive safe integer");
	return e;
}
//#endregion
//#region src/core/chat-controller.ts
var fn = {
	listSessions: !1,
	loadSession: !1,
	resumeSession: !1,
	closeSession: !1,
	deleteSession: !1
}, pn = 16384, mn = 16384, hn = 1024;
function gn(e) {
	return new _n(e);
}
var _n = class {
	#e = new Wt();
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
		this.#o = e, this.#n = dn(e.connector.maxMessageBytes), this.#k = this.#fe(), this.#A = this.#pe(), this.#u = yn(e.context), this.#v = {
			draft: zt,
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
			capabilities: fn,
			sessionTrail: []
		}, vn(e.context) && (this.#c = e.context.subscribe(() => {
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
		this.setDraft(Bt(this.#e.get(t).text, e));
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
		this.setDraft(Vt(this.#e.get(t.instanceId).text, e, t.commands));
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
	refreshComposerActions() {
		this.#v = {
			...this.#v,
			composerActionsRevision: (this.#v.composerActionsRevision ?? 0) + 1
		}, this.#be();
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
		if (!ln({
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
		if (!n(e) || typeof e.text != "string" || e.text.length === 0 || !un(e.text, mn) || e.level !== "info" && e.level !== "error" || e.sessionId !== void 0 && (typeof e.sessionId != "string" || e.sessionId.trim().length === 0)) throw new u("INVALID_CONFIGURATION", `Notice text must contain 1 to ${mn} UTF-8 bytes, use an info or error level, and target a non-empty session ID when provided`, { phase: "notice" });
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
		let n = xn(e);
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
		t.activeTurn = a, t.timeline.beginTurn();
		let o = Date.now();
		t.updatedAt = new Date(o).toISOString(), t.timeline.addUserMessage(n, !0, o), t.phase = "running", t.stopReason = void 0, t.error = void 0, this.#ue(t, !0), this.#xe({
			type: "turn_started",
			sessionId: t.sessionId,
			turnId: r
		});
		let s = this.#z(a, n);
		return s.catch(() => void 0), {
			id: r,
			done: s
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
		if (!n || n.cancelled || (n.cancelled = !0, n.abort.abort(Mn), this.#X(t.sessionId), t.phase = "cancelling", this.#ue(t, !0), !n.submitted)) return;
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
					sessions: jn([...this.#v.sessions.sessions, ...t.sessions]).slice(0, 1e3),
					...t.nextCursor ? { nextCursor: t.nextCursor } : {}
				} : t;
				return this.#Ce(r.sessions), this.#v = bn({
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
			this.#v.sessions && (this.#v = bn({
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
		let i = n?.timeline ?? r.timeline, a = i.reduce(t, this.#_?.version ?? 1);
		if (n) {
			a.state === "idle" && a.stopReason && i.markFinalAnswer(void 0, a.stopReason === "end_turn"), this.#K(n, a);
			return;
		}
		let o = this.#W(r, a);
		this.#ue(r, o);
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
		if (this.#C) throw U();
		let t = ++this.#T;
		this.#p?.abort();
		let n = new AbortController();
		this.#p = n, this.#E = "connecting", this.#D = void 0, this.#ye();
		let r = this.#_, i = this.#v.sessionId, a = this.#O, o = [...this.#d.values()];
		r && (this.#_ = void 0, await r.close().catch(() => void 0), this.#ke(t));
		let s;
		try {
			if (s = await en({
				connector: this.#o.connector,
				protocol: this.#o.protocol ?? 1,
				signal: n.signal,
				sink: this,
				clientInfo: {
					name: this.#o.clientInfo?.name ?? "pretty-aui",
					version: this.#o.clientInfo?.version ?? Lt.version,
					...this.#o.clientInfo?.title ? { title: this.#o.clientInfo.title } : {}
				},
				...this.#o.host ? { host: this.#o.host } : {}
			}), !this.#Oe(t)) throw await s.close().catch(() => void 0), U();
			if (this.#_ = s, this.#v = bn({
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
				e.updatedAt && (l.updatedAt = e.updatedAt), l.lastSelected = e.lastSelected, l.usage = e.usage, e.sessionId === i && this.#ce(l, a);
			} catch (t) {
				if (e.sessionId === i) throw t;
				e.phase = "error", e.error = l(t), this.#d.set(e.sessionId, e);
			} finally {
				this.#f.delete(e.sessionId);
			}
			this.#E = "ready", this.#ye();
		} catch (e) {
			if (!this.#Oe(t)) throw s && this.#_ === s && (this.#_ = void 0), await s?.close().catch(() => void 0), U();
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
			Nn(e.abort.signal);
			let o = a.map((e) => ({
				...e,
				content: e.content.map((t) => Sn(t, e))
			})), s = o.length ? i(t, x()) : t, c = [...o.flatMap((e) => e.content), ...s];
			C(c, n.initialized.promptCapabilities, n.version), this.#I(r.sessionId, c), Nn(e.abort.signal), e.submitted = !0;
			let l = await n.prompt(r.sessionId, c, () => {
				this.#C || (e.dispatched = !0, e.draft && this.#e.dispatched(e.draft.key), r.timeline.markUserAccepted(o), this.#ue(r));
			});
			return this.#Se(e, e.cancelled ? "cancelled" : l);
		} catch (t) {
			if (e.draft && !this.#C && ((!e.dispatched || t instanceof u && t.accepted === !1) && this.#e.failed(e.draft.key, e.draft.submission), this.#e.settled(e.draft.key)), e.cancelled || t === Mn) return this.#Se(e, "cancelled");
			let n = this.#d.get(e.sessionId);
			throw n?.activeTurn === e && (n.activeTurn = void 0, n.timeline.finishTurn()), this.#ie(t, e.sessionId), t;
		}
	}
	async #B(e, t, r, i) {
		try {
			let a = this.#o.context;
			if (!a) return [];
			let o = vn(a) ? await Pn(a.resolve({
				sessionId: e,
				input: t,
				selection: r,
				...this.#v.protocolVersion ? { protocolVersion: this.#v.protocolVersion } : {},
				capabilities: this.#re().initialized.promptCapabilities,
				signal: i
			}), i) : a;
			if (vn(a) && (o.length !== r.length || o.some((e, t) => e.id !== r[t]?.id))) throw Error("Resolved context IDs must match the frozen selection order");
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
				content: e.content.map(Cn)
			})), l = this.#re();
			return C(c.flatMap((e) => e.content), l.initialized.promptCapabilities, l.version), c;
		} catch (e) {
			throw i.aborted ? i.reason ?? e : new u("CONTEXT_FAILED", En(e), {
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
		let n = Tn(t.configOptions), r = this.#k;
		if (!n || !r || n.currentValue === r || !n.options?.some((e) => e.value === r)) return t;
		try {
			let i = await e.setConfigOption(t.sessionId, n.id, r);
			return this.#De(e), On(t, n, r, i);
		} catch {
			if (this.#De(e), this.#E === "error") throw U();
			return this.#xe({
				type: "diagnostic",
				sessionId: t.sessionId,
				code: "MODEL_PREFERENCE_APPLY_FAILED",
				message: "The preferred model could not be applied; using the Agent default"
			}), t;
		}
	}
	async #U(e, t) {
		let n = Dn(t.configOptions), r = this.#A;
		if (!n || !r || n.currentValue === r || !n.options?.some((e) => e.value === r)) return t;
		try {
			let i = await e.setConfigOption(t.sessionId, n.id, r);
			return this.#De(e), On(t, n, r, i);
		} catch {
			if (this.#De(e), this.#E === "error") throw U();
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
		if (this.#C) throw U();
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
		if (this.#C) throw U();
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
		e.lastSelected = ++this.#b, this.#de(e), this.#O = [...t], this.#v = bn({
			...this.#v,
			sessionId: e.sessionId
		}), this.#ye(), this.#xe({
			type: "session_changed",
			sessionId: e.sessionId
		}), e.sessionTitle === void 0 && e.sessionTitleSource !== "notification" && this.#we();
	}
	#le() {
		this.#O = [], this.#v = bn({
			...this.#v,
			sessionId: void 0
		}), this.#ye(), this.#xe({ type: "session_changed" });
	}
	#ue(e, t = !1) {
		this.#v.sessionId === e.sessionId ? (this.#de(e), this.#ye()) : t && this.#ye();
	}
	#de(e) {
		let t = Tn(e.configOptions);
		if (!(!t || typeof t.currentValue != "string" || !kn(t.currentValue) || this.#k === t.currentValue)) {
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
			if (kn(e)) return e;
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
			if (An(e)) return e;
			this.#xe({
				type: "diagnostic",
				code: "INVALID_NEW_SESSION_MODE",
				message: "Ignored an invalid fixed new-session mode"
			});
		}
	}
	#me(e) {
		if (this.#C) throw U();
		let t = this.#o.context;
		if (!vn(t)) throw new u("METHOD_NOT_AVAILABLE", "The configured context is not mutable", { phase: `context/${e}` });
		return t;
	}
	async #he(e, t) {
		if (this.#C) throw U();
		if (this.#l) throw new u("SESSION_BUSY", "Wait for the current context change to finish", { phase: e });
		let n = Symbol(e);
		this.#l = n, this.#ye();
		try {
			if (await t(), this.#C || this.#l !== n) throw U();
			this.#ge();
		} catch (t) {
			throw this.#C ? U() : new u("CONTEXT_FAILED", "Context selection could not be changed", {
				cause: t,
				phase: e,
				retryable: !0
			});
		} finally {
			this.#l === n && (this.#l = void 0, this.#ye());
		}
	}
	#ge() {
		this.#u = yn(this.#o.context), this.#ye();
	}
	#_e() {
		let e = this.#o.context;
		return {
			items: this.#u,
			canAdd: !!(vn(e) && e.add),
			canRemove: !!(vn(e) && e.remove),
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
		this.#v = bn({
			composerActionsRevision: this.#v.composerActionsRevision,
			protocolVersion: this.#v.protocolVersion,
			agentName: this.#v.agentName,
			loadedSessions: [...this.#d.values()].map((e) => ({
				sessionId: e.sessionId,
				...e.sessionTitle ? { title: e.sessionTitle } : {},
				...e.updatedAt ? { updatedAt: e.updatedAt } : {},
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
			draft: e ? this.#e.get(e.instanceId) : zt,
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
		if (this.#C) throw U();
		let n = this.#oe(e.sessionId);
		e.draft && (this.#e.settled(e.draft.key), e.dispatched || this.#e.unlock(e.draft.key)), n.activeTurn === e && (n.activeTurn = void 0);
		let r = Date.now();
		return n.updatedAt = new Date(r).toISOString(), n.timeline.finishTurn(t === "end_turn" ? r : void 0), n.phase = this.#_?.promptReady(n.sessionId) ? "idle" : "cancelling", n.stopReason = t, this.#ue(n, !0), this.#xe({
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
		if (this.#C) throw U();
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
		if (this.#C) throw U();
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
		if (this.#C || this.#_ !== e) throw U();
	}
	#Oe(e) {
		return !this.#C && this.#T === e;
	}
	#ke(e, t) {
		if (!this.#Oe(e) || t !== void 0 && this.#_ !== t) throw U();
	}
};
function vn(e) {
	return !Array.isArray(e) && n(e) && typeof e.getSelection == "function" && typeof e.subscribe == "function" && typeof e.resolve == "function";
}
function yn(e) {
	if (!e) return Object.freeze([]);
	let t = vn(e) ? e.getSelection() : e;
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
function bn(e) {
	let t = { ...e };
	for (let [e, n] of Object.entries(t)) n === void 0 && delete t[e];
	return t;
}
function xn(e) {
	return typeof e == "string" ? [{
		type: "text",
		text: e
	}] : Array.isArray(e) ? [...e] : [e];
}
function Sn(e, t) {
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
function Cn(e) {
	if (!n(e) || typeof e.type != "string" || !e.type) throw Error("Context content blocks require a type");
	if (n(e._meta) && Object.hasOwn(e._meta, "pretty-aui/context")) throw Error("Context blocks cannot use reserved pretty-aui metadata");
	let t = wn(e);
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
function wn(e) {
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
function Tn(e) {
	return e.find((e) => e.category === "model" && e.type === "select") ?? e.find((e) => e.id === "model" && e.type === "select");
}
function En(e) {
	let t = "Context could not be prepared; the prompt was not sent";
	if (!(e instanceof Error)) return t;
	let n = e.message.trim();
	if (!n) return t;
	let r = n.slice(0, hn), i = r.charCodeAt(r.length - 1);
	return i >= 55296 && i <= 56319 && (r = r.slice(0, -1)), n.length > hn && (r += "…"), `${t}: ${r}`;
}
function Dn(e) {
	return e.find((e) => e.category === "mode" && e.type === "select") ?? e.find((e) => e.id === "mode" && e.type === "select");
}
function On(e, t, n, r) {
	return {
		...e,
		configOptions: r.length ? r : e.configOptions.map((e) => e.id === t.id ? {
			...e,
			currentValue: n
		} : e)
	};
}
function kn(e) {
	return An(e);
}
function An(e) {
	return typeof e == "string" && e.length > 0 && un(e, pn);
}
function jn(e) {
	let t = /* @__PURE__ */ new Set();
	return e.filter((e) => !t.has(e.sessionId) && (t.add(e.sessionId), !0));
}
var Mn = Symbol("turn-cancelled");
function Nn(e) {
	if (e.aborted) throw e.reason ?? Mn;
}
function Pn(e, t) {
	return t.aborted ? Promise.reject(t.reason ?? Mn) : new Promise((n, r) => {
		let i = () => {
			r(t.reason ?? Mn);
		};
		t.addEventListener("abort", i, { once: !0 }), Promise.resolve(e).then((e) => {
			t.removeEventListener("abort", i), n(e);
		}, (e) => {
			t.removeEventListener("abort", i), r(e);
		});
	});
}
function U() {
	return new u("CONNECTION_CLOSED", "Chat ownership ended before the operation completed", {
		phase: "connection",
		retryable: !1
	});
}
//#endregion
//#region node_modules/.pnpm/preact@10.29.8/node_modules/preact/jsx-runtime/dist/jsxRuntime.module.js
var Fn = 0;
Array.isArray;
function W(e, t, n, r, i, a) {
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
		__v: --Fn,
		__i: -1,
		__u: 0,
		__source: i,
		__self: a
	};
	if (typeof e == "function" && (o = e.defaultProps)) for (s in o) c[s] === void 0 && (c[s] = o[s]);
	return O.vnode && O.vnode(l), l;
}
//#endregion
//#region src/react/ModelMenu.tsx
var In = (e) => e.options?.find((t) => t.value === e.currentValue)?.name ?? String(e.currentValue);
function Ln(e) {
	let t = e.value.indexOf("/"), n = t > 0 && t < e.value.length - 1 ? e.value.slice(0, t) : void 0, r = e.group ?? n;
	if (!r) return e;
	let i = e.name.indexOf("/"), a = i > 0 ? e.name.slice(0, i).toLowerCase() : void 0, o = a && i < e.name.length - 1 && (a === n?.toLowerCase() || a === r.toLowerCase()) ? e.name.slice(i + 1) : e.name;
	return r === e.group && o === e.name ? e : {
		...e,
		group: r,
		name: o
	};
}
function Rn(e, t) {
	let n = e.toLowerCase();
	if (n.startsWith(t)) return 0;
	let r = -1, i = -1;
	for (let e of t) {
		if (i = n.indexOf(e, i + 1), i < 0) return Infinity;
		r < 0 && (r = i);
	}
	return 1 + (i - r) + r / (1 + n.length);
}
function zn({ model: e, effort: t, labels: n, onSelect: r, runAction: i }) {
	let [a, o] = z(null), [s, c] = z(""), [l, u] = z(), [d, f] = z(!1), p = V(null), m = V(null), h = V(null), g = V(null), _ = H(), v = a === "effort" && t ? t : e, y = a === "model" && (e.options?.length ?? 0) > 4, b = !!(e.currentValue || t?.options?.length), x = Qe(() => {
		let t = String(e.currentValue), n = e.options?.find((e) => e.value === t);
		return Ln(n ?? {
			value: t,
			name: t
		}).name;
	}, [e.currentValue, e.options]), S = Qe(() => {
		if (a !== "model") return [];
		let e = /* @__PURE__ */ new Map();
		for (let t of v.options ?? []) {
			let n = Ln(t), r = e.get(n.group);
			r ? r.push(n) : e.set(n.group, [n]);
		}
		return [...e.values()];
	}, [a, v.options]), C = Qe(() => {
		if (a === "effort") return v.options ?? [];
		let e = s.trim().toLowerCase();
		return e ? S.flatMap((t) => t.map((t) => ({
			item: t,
			score: Math.min(Rn(t.name, e), t.group ? Rn(`${t.group}/${t.name}`, e) : Infinity)
		})).filter(({ score: e }) => Number.isFinite(e)).sort((e, t) => e.score - t.score).map(({ item: e }) => e)) : S.flat();
	}, [
		a,
		v.options,
		S,
		s
	]), w = Math.max(0, C.findIndex((e) => e.value === (l ?? v.currentValue))), T = () => Array.from(p.current?.querySelectorAll(":is([role^=\"menuitem\"],[role=\"option\"]):not(:disabled)") ?? []), E = (e) => {
		g.current = a, c(""), u(void 0), o(e);
	}, D = (e = !0) => {
		o(null), e && m.current?.focus();
	}, O = () => {
		a === "root" || !b ? D() : E("root");
	};
	Ze(() => {
		a && (a === "root" ? (p.current?.querySelector(`[data-pane="${g.current ?? "model"}"]:enabled`) ?? T()[0])?.focus() : h.current && !window.matchMedia?.("(pointer: coarse)").matches ? h.current.focus() : (p.current?.querySelector("[aria-checked=\"true\"]") ?? T()[0])?.focus());
	}, [a]), B(() => {
		if (!a) return;
		let e = (e) => {
			e.composedPath().includes(p.current) || D(!1);
		};
		return document.addEventListener("pointerdown", e), document.addEventListener("focusin", e), () => {
			document.removeEventListener("pointerdown", e), document.removeEventListener("focusin", e);
		};
	}, [a]), B(() => {
		y && p.current?.querySelector("[data-active=\"true\"]")?.scrollIntoView?.({ block: "nearest" });
	}, [
		y,
		w,
		s
	]);
	let ee = (e) => {
		D(), e.value !== v.currentValue && (f(!0), i(async () => {
			try {
				await r(v.id, e.value);
			} finally {
				f(!1);
			}
		}));
	}, k = () => E(b ? "root" : "model");
	function te(e) {
		if (e.nativeEvent.isComposing) return;
		let t = e.key;
		if (!a) {
			if (d) return;
			(t === "ArrowDown" || t === "ArrowUp") && (e.preventDefault(), k());
			return;
		}
		let n = e.target === h.current;
		if (t === "Escape" || t === "ArrowLeft" && !n || t === "Tab" && e.shiftKey) {
			e.preventDefault(), e.stopPropagation(), O();
			return;
		}
		let r = T(), i = r.indexOf(e.target);
		if ([
			"ArrowDown",
			"ArrowUp",
			"Home",
			"End"
		].includes(t) && !(n && (t === "Home" || t === "End"))) {
			if (e.preventDefault(), !r.length) return;
			let a = n ? w : i, o = t === "Home" ? 0 : t === "End" || a < 0 && t === "ArrowUp" ? r.length - 1 : (a + (t === "ArrowUp" ? -1 : 1) + r.length) % r.length;
			y ? (u(C[o].value), h.current?.focus()) : r[o]?.focus();
		} else (t === "Tab" || n && t === "Enter" || a === "root" && t === "ArrowRight") && (e.preventDefault(), n && C[w] ? ee(C[w]) : i >= 0 ? r[i]?.click() : r.length ? r[0]?.focus() : O());
	}
	let ne;
	return /* @__PURE__ */ W("div", {
		ref: p,
		className: "paui-config__field paui-model",
		onKeyDown: te,
		children: [/* @__PURE__ */ W("button", {
			ref: m,
			disabled: !e.options?.length && !t?.options?.length,
			type: "button",
			className: "paui-config__trigger",
			"aria-label": e.name,
			"aria-controls": a ? _ : void 0,
			"aria-haspopup": "menu",
			"aria-expanded": !!a,
			"aria-busy": d,
			"aria-disabled": d || void 0,
			title: [x, t && In(t)].filter(Boolean).join(" · "),
			onClick: () => {
				d || (a ? D() : k());
			},
			children: [
				/* @__PURE__ */ W("span", { children: x || e.name }),
				t && /* @__PURE__ */ W("span", {
					className: "paui-model__effort",
					children: In(t)
				}),
				d ? /* @__PURE__ */ W("span", { className: "paui-session__spinner" }) : /* @__PURE__ */ W("i", {
					className: "paui-model__chevron",
					"aria-hidden": "true"
				})
			]
		}), a && /* @__PURE__ */ W("div", {
			id: _,
			className: "paui-config__listbox paui-model__panel",
			"aria-label": v.name,
			role: "menu",
			children: a === "root" ? [e, ...t ? [t] : []].map((t) => /* @__PURE__ */ W("button", {
				type: "button",
				"data-pane": t === e ? "model" : "effort",
				role: "menuitem",
				className: "paui-config__option paui-model__cell",
				disabled: !t.options?.length,
				onClick: () => E(t === e ? "model" : "effort"),
				children: [
					/* @__PURE__ */ W("b", { children: t.name }),
					" ",
					/* @__PURE__ */ W("span", { children: t === e ? x : In(t) }),
					/* @__PURE__ */ W("i", {
						className: "paui-model__chevron",
						"aria-hidden": "true"
					})
				]
			}, t.id)) : /* @__PURE__ */ W(F, { children: [
				b && /* @__PURE__ */ W("button", {
					type: "button",
					className: "paui-model__back",
					"aria-label": n.back,
					onClick: O,
					children: ["‹ ", v.name]
				}),
				y && /* @__PURE__ */ W("input", {
					ref: h,
					type: "search",
					placeholder: n.modelSearch,
					"aria-label": n.modelSearch,
					role: "combobox",
					"aria-expanded": "true",
					"aria-controls": _ + "-choices",
					"aria-haspopup": "listbox",
					"aria-activedescendant": C.length ? _ + "-" + w : void 0,
					value: s,
					onChange: (e) => {
						c(e.target.value), u(void 0);
					}
				}),
				/* @__PURE__ */ W("div", {
					id: _ + "-choices",
					className: "paui-model__choices",
					role: y ? "listbox" : "group",
					"aria-label": v.name,
					children: [C.map((e, t) => {
						let n = e.group && C[t - 1]?.group !== e.group;
						return n && (ne = `${_}-group-${t}`), /* @__PURE__ */ W(F, { children: [n && /* @__PURE__ */ W("div", {
							className: "paui-model__group",
							id: ne,
							children: e.group
						}), /* @__PURE__ */ W("button", {
							type: "button",
							role: y ? "option" : "menuitemradio",
							id: _ + "-" + t,
							className: "paui-config__option",
							"aria-checked": y ? void 0 : e.value === v.currentValue,
							"aria-selected": y ? e.value === v.currentValue : void 0,
							"data-active": y && w === t || void 0,
							tabIndex: -1,
							"aria-describedby": e.group ? ne : void 0,
							title: e.description ?? e.name,
							onMouseEnter: (t) => {
								y ? u(e.value) : t.currentTarget.focus({ preventScroll: !0 });
							},
							onMouseDown: (e) => e.preventDefault(),
							onClick: () => ee(e),
							children: [/* @__PURE__ */ W("span", { children: e.name }), /* @__PURE__ */ W("span", {
								className: "paui-config__check",
								"aria-hidden": "true",
								children: e.value === v.currentValue ? "✓" : ""
							})]
						})] }, e.value);
					}), !C.length && /* @__PURE__ */ W("small", {
						role: "status",
						children: n.noMatchingModels
					})]
				})
			] })
		})]
	});
}
//#endregion
//#region src/react/composer-images.ts
var Bn = Promise.resolve(), Vn = 0, Hn = class extends Error {
	issue;
	constructor(e) {
		super(`Image validation failed: ${e}`), this.issue = e;
	}
};
function Un(e) {
	let t = Bn.then(async () => {
		let t = Uint8Array.from(atob(e.data), (e) => e.charCodeAt(0)), n = URL.createObjectURL(new Blob([t], { type: e.mimeType })), r = new Image();
		try {
			return r.src = n, await r.decode(), n;
		} catch (e) {
			throw URL.revokeObjectURL(n), e;
		} finally {
			r.src = "";
		}
	});
	return Bn = t.then(() => void 0, () => void 0), t;
}
function Wn(e, t) {
	let n = Bn.then(async () => {
		if (e.length + t.length > 4) throw new Hn("count");
		let n = Rt - Ht(t), r = [];
		for (let t of e) {
			let e = 4 * Math.ceil(t.size / 3);
			if (!t.size || e > n) throw new Hn("budget");
			let i = new Uint8Array(await t.arrayBuffer()), a = Gn(i);
			if (!a || t.type && t.type !== a) throw new Hn("type");
			let o = Kn(i, a);
			o && qn(...o), await Jn(new Blob([i], { type: a }));
			let s = "";
			for (let e = 0; e < i.length; e += 32768) s += String.fromCharCode(...i.subarray(e, e + 32768));
			r.push({
				type: "image",
				id: `image-${++Vn}`,
				name: t.name || "image",
				mimeType: a,
				data: btoa(s)
			}), n -= e;
		}
		return r;
	}).catch((e) => {
		throw e instanceof Hn ? e : new Hn("decode");
	});
	return Bn = n.then(() => void 0, () => void 0), n;
}
function Gn(e) {
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
function Kn(e, t) {
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
function qn(e, t) {
	if (e <= 0 || t <= 0 || e > 8e3 || t > 8e3 || e * t > 16e6) throw new Hn("dimensions");
}
async function Jn(e) {
	if (typeof createImageBitmap == "function") {
		let t = await createImageBitmap(e);
		try {
			qn(t.width, t.height);
		} finally {
			t.close();
		}
		return;
	}
	let t = URL.createObjectURL(e), n = new Image();
	try {
		n.src = t, await n.decode(), qn(n.naturalWidth, n.naturalHeight);
	} finally {
		n.src = "", URL.revokeObjectURL(t);
	}
}
//#endregion
//#region src/react/ComposerImages.tsx
function Yn({ images: e, sessionInstanceId: t, disabled: n, remove: r, labels: i }) {
	let [a, o] = z(/* @__PURE__ */ new Map());
	return B(() => {
		let t = !0, n = /* @__PURE__ */ new Map();
		return o(/* @__PURE__ */ new Map()), (async () => {
			for (let r of e) {
				if (!t) break;
				try {
					let e = await Un(r);
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
	}, [e, t]), /* @__PURE__ */ W(F, { children: e.map((e) => /* @__PURE__ */ W("span", {
		className: "paui-context-chip",
		children: [
			a.get(e.id) && /* @__PURE__ */ W("img", {
				src: a.get(e.id),
				alt: e.name
			}),
			/* @__PURE__ */ W("span", { children: e.name }),
			/* @__PURE__ */ W("button", {
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
function Xn({ label: e, variant: t, actions: n, disabled: r, onChoose: i, onOpen: a }) {
	let [o, s] = z(!1), c = H(), l = V(null), u = V(null);
	Ze(() => o ? Qn(u.current) : void 0, [o]);
	let d = () => {
		s(!1), l.current?.focus();
	};
	B(() => {
		if (!o) return;
		u.current?.querySelector("button:not(:disabled)")?.focus();
		let e = (e) => {
			!e.composedPath().includes(u.current) && !e.composedPath().includes(l.current) && s(!1);
		};
		return document.addEventListener("pointerdown", e), document.addEventListener("focusin", e), () => {
			document.removeEventListener("pointerdown", e), document.removeEventListener("focusin", e);
		};
	}, [o]);
	function f(e, t) {
		return e.map((e, n) => {
			let r = `${t}-${n}`;
			return e.children ? e.children.length ? /* @__PURE__ */ W("div", {
				role: "group",
				"aria-label": e.label,
				children: [/* @__PURE__ */ W("small", { children: e.label }), f(e.children, r)]
			}, e.id) : null : /* @__PURE__ */ W("button", {
				type: "button",
				role: "menuitem",
				"data-action": e.id,
				disabled: e.disabled,
				"aria-label": e.label,
				"aria-describedby": e.description ? r : void 0,
				title: e.description,
				onClick: () => {
					d(), i(e);
				},
				children: [/* @__PURE__ */ W("span", { children: e.label }), e.description && /* @__PURE__ */ W("small", {
					id: r,
					children: e.description
				})]
			}, e.id);
		});
	}
	return /* @__PURE__ */ W("div", {
		className: "paui-composer-menu",
		children: [/* @__PURE__ */ W("button", {
			ref: l,
			type: "button",
			className: t === "add" ? "paui-context-add" : "paui-shortcut",
			"aria-label": e,
			"aria-haspopup": "menu",
			"aria-expanded": o,
			disabled: r,
			onClick: () => {
				o || a(), s(!o);
			},
			children: t === "add" ? "+" : e
		}), o && /* @__PURE__ */ W("div", {
			ref: u,
			role: "menu",
			"aria-label": e,
			className: "paui-composer-menu__panel",
			onKeyDown: (e) => {
				e.key === "Escape" || e.key === "ArrowLeft" ? (e.preventDefault(), e.stopPropagation(), d()) : e.key === "Tab" ? s(!1) : Zn(e);
			},
			children: f(typeof n == "function" ? n() : n, c)
		})]
	});
}
function Zn(e) {
	if (![
		"ArrowDown",
		"ArrowUp",
		"Home",
		"End"
	].includes(e.key)) return;
	let t = Array.from(e.currentTarget.querySelectorAll("button[role=\"menuitem\"]:not(:disabled)"));
	if (!t.length) return;
	e.preventDefault();
	let n = t.indexOf(e.target);
	t[e.key === "Home" ? 0 : e.key === "End" ? t.length - 1 : (n + (e.key === "ArrowDown" ? 1 : -1) + t.length) % t.length]?.focus();
}
function Qn(e) {
	let t = e?.closest(".paui-composer-wrap")?.querySelector(".paui-composer-unit"), n = e?.closest(".pretty-aui");
	if (!e || !t || !n) return;
	let r = () => {
		let r = t.getBoundingClientRect().top - n.getBoundingClientRect().top - 8;
		e.style.maxHeight = Math.max(48, Math.min(320, Math.floor(r))) + "px";
	};
	r();
	let i = globalThis.ResizeObserver ? new ResizeObserver(r) : void 0;
	return i?.observe(n), i?.observe(t), () => i?.disconnect();
}
//#endregion
//#region node_modules/.pnpm/dompurify@3.4.14/node_modules/dompurify/dist/purify.es.mjs
function $n(e, t) {
	(t == null || t > e.length) && (t = e.length);
	for (var n = 0, r = Array(t); n < t; n++) r[n] = e[n];
	return r;
}
function er(e) {
	if (Array.isArray(e)) return e;
}
function tr(e, t) {
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
function nr() {
	throw TypeError("Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.");
}
function rr(e, t) {
	return er(e) || tr(e, t) || ir(e, t) || nr();
}
function ir(e, t) {
	if (e) {
		if (typeof e == "string") return $n(e, t);
		var n = {}.toString.call(e).slice(8, -1);
		return n === "Object" && e.constructor && (n = e.constructor.name), n === "Map" || n === "Set" ? Array.from(e) : n === "Arguments" || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n) ? $n(e, t) : void 0;
	}
}
var ar = Object.entries, or = Object.setPrototypeOf, sr = Object.isFrozen, cr = Object.getPrototypeOf, lr = Object.getOwnPropertyDescriptor, G = Object.freeze, K = Object.seal, ur = Object.create, dr = typeof Reflect < "u" && Reflect, fr = dr.apply, pr = dr.construct;
G ||= function(e) {
	return e;
}, K ||= function(e) {
	return e;
}, fr ||= function(e, t) {
	var n = [...arguments].slice(2);
	return e.apply(t, n);
}, pr ||= function(e) {
	return new e(...[...arguments].slice(1));
};
var mr = J(Array.prototype.forEach), hr = J(Array.prototype.lastIndexOf), gr = J(Array.prototype.pop), _r = J(Array.prototype.push), vr = J(Array.prototype.splice), yr = Array.isArray, br = J(String.prototype.toLowerCase), xr = J(String.prototype.toString), Sr = J(String.prototype.match), Cr = J(String.prototype.replace), wr = J(String.prototype.indexOf), Tr = J(String.prototype.trim), Er = J(Number.prototype.toString), Dr = J(Boolean.prototype.toString), Or = typeof BigInt > "u" ? null : J(BigInt.prototype.toString), kr = typeof Symbol > "u" ? null : J(Symbol.prototype.toString), Ar = J(Object.prototype.hasOwnProperty), jr = J(Object.prototype.toString), q = J(RegExp.prototype.test), Mr = Nr(TypeError);
function J(e) {
	return function(t) {
		t instanceof RegExp && (t.lastIndex = 0);
		var n = [...arguments].slice(1);
		return fr(e, t, n);
	};
}
function Nr(e) {
	return function() {
		return pr(e, [...arguments]);
	};
}
function Y(e, t) {
	let n = arguments.length > 2 && arguments[2] !== void 0 ? arguments[2] : br;
	if (or && or(e, null), !yr(t)) return e;
	let r = t.length;
	for (; r--;) {
		let i = t[r];
		if (typeof i == "string") {
			let e = n(i);
			e !== i && (sr(t) || (t[r] = e), i = e);
		}
		e[i] = !0;
	}
	return e;
}
function Pr(e) {
	for (let t = 0; t < e.length; t++) Ar(e, t) || (e[t] = null);
	return e;
}
function Fr(e) {
	let t = ur(null);
	for (let r of ar(e)) {
		var n = rr(r, 2);
		let i = n[0], a = n[1];
		Ar(e, i) && (t[i] = yr(a) ? Pr(a) : a && typeof a == "object" && a.constructor === Object ? Fr(a) : a);
	}
	return t;
}
function Ir(e) {
	switch (typeof e) {
		case "string": return e;
		case "number": return Er(e);
		case "boolean": return Dr(e);
		case "bigint": return Or ? Or(e) : "0";
		case "symbol": return kr ? kr(e) : "Symbol()";
		case "undefined": return jr(e);
		case "function":
		case "object": {
			if (e === null) return jr(e);
			let t = e, n = Lr(t, "toString");
			if (typeof n == "function") {
				let e = n(t);
				return typeof e == "string" ? e : jr(e);
			}
			return jr(e);
		}
		default: return jr(e);
	}
}
function Lr(e, t) {
	for (; e !== null;) {
		let n = lr(e, t);
		if (n) {
			if (n.get) return J(n.get);
			if (typeof n.value == "function") return J(n.value);
		}
		e = cr(e);
	}
	function n() {
		return null;
	}
	return n;
}
function Rr(e) {
	try {
		return q(e, ""), !0;
	} catch {
		return !1;
	}
}
var zr = G(/* @__PURE__ */ "a.abbr.acronym.address.area.article.aside.audio.b.bdi.bdo.big.blink.blockquote.body.br.button.canvas.caption.center.cite.code.col.colgroup.content.data.datalist.dd.decorator.del.details.dfn.dialog.dir.div.dl.dt.element.em.fieldset.figcaption.figure.font.footer.form.h1.h2.h3.h4.h5.h6.head.header.hgroup.hr.html.i.img.input.ins.kbd.label.legend.li.main.map.mark.marquee.menu.menuitem.meter.nav.nobr.ol.optgroup.option.output.p.picture.pre.progress.q.rp.rt.ruby.s.samp.search.section.select.shadow.slot.small.source.spacer.span.strike.strong.style.sub.summary.sup.table.tbody.td.template.textarea.tfoot.th.thead.time.tr.track.tt.u.ul.var.video.wbr".split(".")), Br = G(/* @__PURE__ */ "svg.a.altglyph.altglyphdef.altglyphitem.animatecolor.animatemotion.animatetransform.circle.clippath.defs.desc.ellipse.enterkeyhint.exportparts.filter.font.g.glyph.glyphref.hkern.image.inputmode.line.lineargradient.marker.mask.metadata.mpath.part.path.pattern.polygon.polyline.radialgradient.rect.stop.style.switch.symbol.text.textpath.title.tref.tspan.view.vkern".split(".")), Vr = G([
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
]), Hr = G([
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
]), Ur = G(/* @__PURE__ */ "math.menclose.merror.mfenced.mfrac.mglyph.mi.mlabeledtr.mmultiscripts.mn.mo.mover.mpadded.mphantom.mroot.mrow.ms.mspace.msqrt.mstyle.msub.msup.msubsup.mtable.mtd.mtext.mtr.munder.munderover.mprescripts".split(".")), Wr = G([
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
]), Gr = G(["#text"]), Kr = G(/* @__PURE__ */ "accept.action.align.alt.autocapitalize.autocomplete.autopictureinpicture.autoplay.background.bgcolor.border.capture.cellpadding.cellspacing.checked.cite.class.clear.color.cols.colspan.command.commandfor.controls.controlslist.coords.crossorigin.datetime.decoding.default.dir.disabled.disablepictureinpicture.disableremoteplayback.download.draggable.enctype.enterkeyhint.exportparts.face.for.headers.height.hidden.high.href.hreflang.id.inert.inputmode.integrity.ismap.kind.label.lang.list.loading.loop.low.max.maxlength.media.method.min.minlength.multiple.muted.name.nonce.noshade.novalidate.nowrap.open.optimum.part.pattern.placeholder.playsinline.popover.popovertarget.popovertargetaction.poster.preload.pubdate.radiogroup.readonly.rel.required.rev.reversed.role.rows.rowspan.spellcheck.scope.selected.shape.size.sizes.slot.span.srclang.start.src.srcset.step.style.summary.tabindex.title.translate.type.usemap.valign.value.width.wrap.xmlns".split(".")), qr = G(/* @__PURE__ */ "accent-height.accumulate.additive.alignment-baseline.amplitude.ascent.attributename.attributetype.azimuth.basefrequency.baseline-shift.begin.bias.by.class.clip.clippathunits.clip-path.clip-rule.color.color-interpolation.color-interpolation-filters.color-profile.color-rendering.cx.cy.d.dx.dy.diffuseconstant.direction.display.divisor.dominant-baseline.dur.edgemode.elevation.end.exponent.fill.fill-opacity.fill-rule.filter.filterunits.flood-color.flood-opacity.font-family.font-size.font-size-adjust.font-stretch.font-style.font-variant.font-weight.fx.fy.g1.g2.glyph-name.glyphref.gradientunits.gradienttransform.height.href.id.image-rendering.in.in2.intercept.k.k1.k2.k3.k4.kerning.keypoints.keysplines.keytimes.lang.lengthadjust.letter-spacing.kernelmatrix.kernelunitlength.lighting-color.local.marker-end.marker-mid.marker-start.markerheight.markerunits.markerwidth.maskcontentunits.maskunits.max.mask.mask-type.media.method.mode.min.name.numoctaves.offset.operator.opacity.order.orient.orientation.origin.overflow.paint-order.path.pathlength.patterncontentunits.patterntransform.patternunits.pointer-events.points.preservealpha.preserveaspectratio.primitiveunits.r.rx.ry.radius.refx.refy.repeatcount.repeatdur.restart.result.rotate.scale.seed.shape-rendering.slope.specularconstant.specularexponent.spreadmethod.startoffset.stddeviation.stitchtiles.stop-color.stop-opacity.stroke-dasharray.stroke-dashoffset.stroke-linecap.stroke-linejoin.stroke-miterlimit.stroke-opacity.stroke.stroke-width.style.surfacescale.systemlanguage.tabindex.tablevalues.targetx.targety.transform.transform-origin.text-anchor.text-decoration.text-orientation.text-rendering.textlength.type.u1.u2.unicode.values.vector-effect.viewbox.visibility.version.vert-adv-y.vert-origin-x.vert-origin-y.width.word-spacing.wrap.writing-mode.xchannelselector.ychannelselector.x.x1.x2.xmlns.y.y1.y2.z.zoomandpan".split(".")), Jr = G(/* @__PURE__ */ "accent.accentunder.align.bevelled.close.columnalign.columnlines.columnspacing.columnspan.denomalign.depth.dir.display.displaystyle.encoding.fence.frame.height.href.id.largeop.length.linethickness.lquote.lspace.mathbackground.mathcolor.mathsize.mathvariant.maxsize.minsize.movablelimits.notation.numalign.open.rowalign.rowlines.rowspacing.rowspan.rspace.rquote.scriptlevel.scriptminsize.scriptsizemultiplier.selection.separator.separators.stretchy.subscriptshift.supscriptshift.symmetric.voffset.width.xmlns".split(".")), Yr = G([
	"xlink:href",
	"xml:id",
	"xlink:title",
	"xml:space",
	"xmlns:xlink"
]), Xr = K(/{{[\w\W]*|^[\w\W]*}}/g), Zr = K(/<%[\w\W]*|^[\w\W]*%>/g), Qr = K(/\${[\w\W]*/g), $r = K(/^data-[\-\w.\u00B7-\uFFFF]+$/), ei = K(/^aria-[\-\w]+$/), ti = K(/^(?:(?:(?:f|ht)tps?|mailto|tel|callto|sms|cid|xmpp|matrix):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i), ni = K(/^(?:\w+script|data):/i), ri = K(/[\u0000-\u0020\u00A0\u1680\u180E\u2000-\u2029\u205F\u3000]/g), ii = K(/^html$/i), ai = K(/^[a-z][.\w]*(-[.\w]+)+$/i), oi = K(/<[/\w!]/g), si = K(/<[/\w]/g), ci = K(/<\/no(script|embed|frames)/i), li = K(/\/>/i), ui = {
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
}, di = [
	"style",
	"script",
	"xmp",
	"iframe",
	"noembed",
	"noframes",
	"plaintext",
	"noscript"
], fi = G(Y({}, di)), pi = function() {
	let e = {};
	return mr(di, (t) => {
		e[t] = K(RegExp("</" + t + "(?=[\\t\\n\\f\\r />])", "i"));
	}), G(e);
}(), mi = function() {
	return typeof window > "u" ? null : window;
}, hi = function(e, t) {
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
}, gi = function() {
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
}, _i = function(e, t, n, r) {
	return Ar(e, t) && yr(e[t]) ? Y(r.base ? Fr(r.base) : {}, e[t], r.transform) : n;
}, vi = function(e, t, n) {
	let r = Ar(e, t) ? e[t] : void 0;
	return r && typeof r == "object" ? Fr(r) : n();
};
function yi() {
	let e = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : mi(), t = (e) => yi(e);
	if (t.version = "3.4.14", t.removed = [], !e || !e.document || e.document.nodeType !== ui.document || !e.Element) return t.isSupported = !1, t;
	let n = e.document, r = n, i = r.currentScript;
	e.DocumentFragment;
	let a = e.HTMLTemplateElement, o = e.Node, s = e.Element, c = e.NodeFilter;
	e.NamedNodeMap === void 0 && (e.NamedNodeMap || e.MozNamedAttrMap), e.HTMLFormElement;
	let l = e.DOMParser, u = e.trustedTypes, d = s.prototype, f = Lr(d, "cloneNode"), p = Lr(d, "remove"), m = Lr(d, "nextSibling"), h = Lr(d, "childNodes"), g = Lr(d, "parentNode"), _ = Lr(d, "shadowRoot"), v = Lr(d, "attributes"), y = o && o.prototype ? Lr(o.prototype, "nodeType") : null, b = o && o.prototype ? Lr(o.prototype, "nodeName") : null, x = o && o.prototype ? Lr(o.prototype, "ownerDocument") : null, S = function(e) {
		return y ? y(e) : e.nodeType;
	}, C = function(e) {
		return b ? b(e) : e.nodeName;
	};
	if (typeof a == "function") {
		let e = n.createElement("template");
		e.content && e.content.ownerDocument && (n = e.content.ownerDocument);
	}
	let w, T = "", E, D = !1, O = 0, ee = function() {
		if (O > 0) throw Mr("A configured TRUSTED_TYPES_POLICY callback (createHTML or createScriptURL) must not call DOMPurify.sanitize, as that causes infinite recursion. Do not pass a policy whose callbacks wrap DOMPurify as TRUSTED_TYPES_POLICY; see the \"DOMPurify and Trusted Types\" section of the README.");
	}, k = function(e) {
		ee(), O++;
		try {
			return w.createHTML(e);
		} finally {
			O--;
		}
	}, te = function(e) {
		ee(), O++;
		try {
			return w.createScriptURL(e);
		} finally {
			O--;
		}
	}, ne = function() {
		return D ||= (E = hi(u, i), !0), E;
	}, re = n, A = re.implementation, ie = re.createNodeIterator, j = re.createDocumentFragment, ae = re.getElementsByTagName, M = r.importNode, N = gi();
	t.isSupported = typeof ar == "function" && typeof g == "function" && A && A.createHTMLDocument !== void 0;
	let oe = Xr, se = Zr, ce = Qr, le = $r, ue = ei, de = ni, fe = ri, pe = ai, me = ti, P = null, F = Y({}, [
		...zr,
		...Br,
		...Vr,
		...Ur,
		...Gr
	]), I = null, he = Y({}, [
		...Kr,
		...qr,
		...Jr,
		...Yr
	]), ge = Object.seal(ur(null, {
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
	})), _e = null, ve = null, ye = Object.seal(ur(null, {
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
	})), be = !0, xe = !0, Se = !1, Ce = !0, we = !1, Te = !0, Ee = !1, De = !1, Oe = null, ke = null, Ae = !1, je = !1, Me = !1, Ne = !1, Pe = !0, Fe = !1, Ie = "user-content-", Le = !0, Re = !1, L = {}, ze = null, Be = Y({}, /* @__PURE__ */ "annotation-xml.audio.colgroup.desc.foreignobject.head.iframe.math.mi.mn.mo.ms.mtext.noembed.noframes.noscript.plaintext.script.selectedcontent.style.svg.template.thead.title.video.xmp".split(".")), Ve = null, He = Y({}, [
		"audio",
		"video",
		"img",
		"source",
		"image",
		"track"
	]), R = null, Ue = Y({}, [
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
	]), We = "http://www.w3.org/1998/Math/MathML", Ge = "http://www.w3.org/2000/svg", Ke = "http://www.w3.org/1999/xhtml", qe = Ke, Je = !1, Ye = null, z = Y({}, [
		We,
		Ge,
		Ke
	], xr), Xe = G([
		"mi",
		"mo",
		"mn",
		"ms",
		"mtext"
	]), B = Y({}, Xe), Ze = G(["annotation-xml"]), V = Y({}, Ze), Qe = Y({}, [
		"title",
		"style",
		"font",
		"a",
		"script"
	]), $e = null, et = ["application/xhtml+xml", "text/html"], H = null, tt = null, nt = n.createElement("form"), rt = function(e) {
		return e instanceof RegExp || e instanceof Function;
	}, it = function() {
		let e = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : {};
		if (tt && tt === e) return;
		(!e || typeof e != "object") && (e = {}), e = Fr(e), $e = et.indexOf(e.PARSER_MEDIA_TYPE) === -1 ? "text/html" : e.PARSER_MEDIA_TYPE, H = $e === "application/xhtml+xml" ? xr : br, P = _i(e, "ALLOWED_TAGS", F, { transform: H }), I = _i(e, "ALLOWED_ATTR", he, { transform: H }), Ye = _i(e, "ALLOWED_NAMESPACES", z, { transform: xr }), R = _i(e, "ADD_URI_SAFE_ATTR", Ue, {
			transform: H,
			base: Ue
		}), Ve = _i(e, "ADD_DATA_URI_TAGS", He, {
			transform: H,
			base: He
		}), ze = _i(e, "FORBID_CONTENTS", Be, { transform: H }), _e = _i(e, "FORBID_TAGS", Fr({}), { transform: H }), ve = _i(e, "FORBID_ATTR", Fr({}), { transform: H }), L = Ar(e, "USE_PROFILES") ? e.USE_PROFILES && typeof e.USE_PROFILES == "object" ? Fr(e.USE_PROFILES) : e.USE_PROFILES : !1, be = e.ALLOW_ARIA_ATTR !== !1, xe = e.ALLOW_DATA_ATTR !== !1, Se = e.ALLOW_UNKNOWN_PROTOCOLS || !1, Ce = e.ALLOW_SELF_CLOSE_IN_ATTR !== !1, we = e.SAFE_FOR_TEMPLATES || !1, Te = e.SAFE_FOR_XML !== !1, Ee = e.WHOLE_DOCUMENT || !1, je = e.RETURN_DOM || !1, Me = e.RETURN_DOM_FRAGMENT || !1, Ne = e.RETURN_TRUSTED_TYPE || !1, Ae = e.FORCE_BODY || !1, Pe = e.SANITIZE_DOM !== !1, Fe = e.SANITIZE_NAMED_PROPS || !1, Le = e.KEEP_CONTENT !== !1, Re = e.IN_PLACE || !1, me = Rr(e.ALLOWED_URI_REGEXP) ? e.ALLOWED_URI_REGEXP : ti, qe = typeof e.NAMESPACE == "string" ? e.NAMESPACE : Ke, B = vi(e, "MATHML_TEXT_INTEGRATION_POINTS", () => Y({}, Xe)), V = vi(e, "HTML_INTEGRATION_POINTS", () => Y({}, Ze));
		let t = vi(e, "CUSTOM_ELEMENT_HANDLING", () => ur(null));
		if (ge = ur(null), Ar(t, "tagNameCheck") && rt(t.tagNameCheck) && (ge.tagNameCheck = t.tagNameCheck), Ar(t, "attributeNameCheck") && rt(t.attributeNameCheck) && (ge.attributeNameCheck = t.attributeNameCheck), Ar(t, "allowCustomizedBuiltInElements") && typeof t.allowCustomizedBuiltInElements == "boolean" && (ge.allowCustomizedBuiltInElements = t.allowCustomizedBuiltInElements), K(ge), we && (xe = !1), Me && (je = !0), L && (P = Y({}, Gr), I = ur(null), L.html === !0 && (Y(P, zr), Y(I, Kr)), L.svg === !0 && (Y(P, Br), Y(I, qr), Y(I, Yr)), L.svgFilters === !0 && (Y(P, Vr), Y(I, qr), Y(I, Yr)), L.mathMl === !0 && (Y(P, Ur), Y(I, Jr), Y(I, Yr))), ye.tagCheck = null, ye.attributeCheck = null, Ar(e, "ADD_TAGS") && (typeof e.ADD_TAGS == "function" ? ye.tagCheck = e.ADD_TAGS : yr(e.ADD_TAGS) && (P === F && (P = Fr(P)), Y(P, e.ADD_TAGS, H))), Ar(e, "ADD_ATTR") && (typeof e.ADD_ATTR == "function" ? ye.attributeCheck = e.ADD_ATTR : yr(e.ADD_ATTR) && (I === he && (I = Fr(I)), Y(I, e.ADD_ATTR, H))), Ar(e, "ADD_FORBID_CONTENTS") && yr(e.ADD_FORBID_CONTENTS) && (ze === Be && (ze = Fr(ze)), Y(ze, e.ADD_FORBID_CONTENTS, H)), Le && (P["#text"] = !0), Ee && Y(P, [
			"html",
			"head",
			"body"
		]), P.table && (Y(P, ["tbody"]), delete _e.tbody), e.TRUSTED_TYPES_POLICY) {
			if (typeof e.TRUSTED_TYPES_POLICY.createHTML != "function") throw Mr("TRUSTED_TYPES_POLICY configuration option must provide a \"createHTML\" hook.");
			if (typeof e.TRUSTED_TYPES_POLICY.createScriptURL != "function") throw Mr("TRUSTED_TYPES_POLICY configuration option must provide a \"createScriptURL\" hook.");
			let t = w;
			w = e.TRUSTED_TYPES_POLICY;
			try {
				T = k("");
			} catch (e) {
				throw w = t, e;
			}
		} else e.TRUSTED_TYPES_POLICY === null ? (w = void 0, T = "") : (w === void 0 && (w = ne()), w && typeof T == "string" && (T = k("")));
		G && G(e), tt = e;
	}, at = Y({}, [
		...Br,
		...Vr,
		...Hr
	]), ot = Y({}, [...Ur, ...Wr]), st = function(e, t, n) {
		return t.namespaceURI === Ke ? e === "svg" : t.namespaceURI === We ? e === "svg" && (n === "annotation-xml" || B[n]) : !!at[e];
	}, ct = function(e, t, n) {
		return t.namespaceURI === Ke ? e === "math" : t.namespaceURI === Ge ? e === "math" && V[n] : !!ot[e];
	}, lt = function(e, t, n) {
		return t.namespaceURI === Ge && !V[n] || t.namespaceURI === We && !B[n] ? !1 : !ot[e] && (Qe[e] || !at[e]);
	}, ut = function(e) {
		let t = g(e);
		(!t || !t.tagName) && (t = {
			namespaceURI: qe,
			tagName: "template"
		});
		let n = br(e.tagName), r = br(t.tagName);
		return Ye[e.namespaceURI] ? e.namespaceURI === Ge ? st(n, t, r) : e.namespaceURI === We ? ct(n, t, r) : e.namespaceURI === Ke ? lt(n, t, r) : !!($e === "application/xhtml+xml" && Ye[e.namespaceURI]) : !1;
	}, dt = function(e) {
		_r(t.removed, { element: e });
		try {
			g(e).removeChild(e);
		} catch {
			if (p(e), !g(e)) throw Mr("a node selected for removal could not be detached from its tree and cannot be safely returned; refusing to sanitize in place");
		}
	}, ft = function(e, t, n) {
		try {
			e.removeAttributeNode(t);
		} catch {
			try {
				e.removeAttribute(n);
			} catch {}
		}
	}, pt = function(e) {
		gt(e);
		let t = h(e);
		if (t) {
			let e = [];
			mr(t, (t) => {
				_r(e, t);
			}), mr(e, (e) => {
				try {
					p(e);
				} catch {}
			});
		}
		let n = v(e);
		if (n) for (let t = n.length - 1; t >= 0; --t) {
			let r = n[t], i = r && r.name;
			typeof i == "string" && ft(e, r, i);
		}
	}, mt = function(e, n, r) {
		if (!r) try {
			r = n.getAttributeNode(e);
		} catch {
			r = null;
		}
		_r(t.removed, {
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
			if (je || Me) try {
				dt(n);
			} catch {}
			else try {
				n.setAttribute(e, "");
			} catch {}
		}
	}, ht = function(e) {
		let t = v(e);
		if (t) for (let n = t.length - 1; n >= 0; --n) {
			let r = t[n], i = r && r.name;
			typeof i != "string" || I[H(i)] || ft(e, r, i);
		}
	}, gt = function(e) {
		let t = [e];
		for (; t.length > 0;) {
			let e = t.pop();
			S(e) === ui.element && ht(e);
			let n = h(e);
			if (n) for (let e = n.length - 1; e >= 0; --e) t.push(n[e]);
		}
	}, _t = function(e, t) {
		return Te ? e === "patchsrc" || e === "for" && t !== "label" && t !== "output" : !1;
	}, vt = function(e) {
		if (!Te) return;
		let t = [e];
		for (; t.length > 0;) {
			let e = t.pop(), n = S(e);
			if (n === ui.processingInstruction || n === ui.comment && q(si, e.data)) {
				try {
					p(e);
				} catch {}
				continue;
			}
			if (n === ui.element) {
				let t = e, n = H(C(e));
				try {
					t.hasAttribute && t.hasAttribute("patchsrc") && t.removeAttribute("patchsrc"), t.hasAttribute && t.hasAttribute("for") && _t("for", n) && t.removeAttribute("for");
				} catch {}
			}
			let r = h(e);
			if (r) for (let e = r.length - 1; e >= 0; --e) t.push(r[e]);
		}
	}, yt = function(e) {
		let t = null, r = null;
		if (Ae) e = "<remove></remove>" + e;
		else {
			let t = Sr(e, /^[\r\n\t ]+/);
			r = t && t[0];
		}
		$e === "application/xhtml+xml" && qe === Ke && (e = "<html xmlns=\"http://www.w3.org/1999/xhtml\"><head></head><body>" + e + "</body></html>");
		let i = w ? k(e) : e;
		if (qe === Ke) try {
			t = new l().parseFromString(i, $e);
		} catch {}
		if (!t || !t.documentElement) {
			t = A.createDocument(qe, "template", null);
			try {
				t.documentElement.innerHTML = Je ? T : i;
			} catch {}
		}
		let a = t.body || t.documentElement;
		return e && r && a.insertBefore(n.createTextNode(r), a.childNodes[0] || null), qe === Ke ? ae.call(t, Ee ? "html" : "body")[0] : Ee ? t.documentElement : a;
	}, bt = function(e) {
		let t = x ? x(e) : e.ownerDocument;
		return ie.call(t || e, e, c.SHOW_ELEMENT | c.SHOW_COMMENT | c.SHOW_TEXT | c.SHOW_PROCESSING_INSTRUCTION | c.SHOW_CDATA_SECTION, null);
	}, xt = function(e) {
		return e = Cr(e, oe, " "), e = Cr(e, se, " "), e = Cr(e, ce, " "), e;
	}, St = function(e) {
		e.normalize();
		let t = x ? x(e) : e.ownerDocument, n = ie.call(t || e, e, c.SHOW_TEXT | c.SHOW_COMMENT | c.SHOW_CDATA_SECTION | c.SHOW_PROCESSING_INSTRUCTION, null), r = n.nextNode();
		for (; r;) r.data = xt(r.data), r = n.nextNode();
		let i = e.querySelectorAll?.call(e, "template");
		i && mr(i, (e) => {
			wt(e.content) && St(e.content);
		});
	}, Ct = function(e) {
		let t = b ? b(e) : null;
		return typeof t != "string" || H(t) !== "form" ? !1 : typeof e.nodeName != "string" || typeof e.textContent != "string" || typeof e.removeChild != "function" || e.attributes !== v(e) || typeof e.removeAttribute != "function" || typeof e.setAttribute != "function" || typeof e.namespaceURI != "string" || typeof e.insertBefore != "function" || typeof e.hasChildNodes != "function" || e.nodeType !== y(e) || e.childNodes !== h(e);
	}, wt = function(e) {
		if (!y || typeof e != "object" || !e) return !1;
		try {
			return y(e) === ui.documentFragment;
		} catch {
			return !1;
		}
	}, Tt = function(e) {
		if (!y || typeof e != "object" || !e) return !1;
		try {
			return typeof y(e) == "number";
		} catch {
			return !1;
		}
	};
	function Et(e, n, r) {
		e.length !== 0 && mr(e, (e) => {
			e.call(t, n, r, tt);
		});
	}
	let Dt = function(e, t) {
		return !!(Te && e.hasChildNodes() && !Tt(e.firstElementChild) && q(oi, e.textContent) && q(oi, e.innerHTML) || Te && e.namespaceURI === Ke && fi[t] && (Tt(e.firstElementChild) || typeof e.textContent == "string" && q(pi[t], e.textContent)) || e.nodeType === ui.processingInstruction || Te && e.nodeType === ui.comment && q(si, e.data));
	}, Ot = function(e, t) {
		return e instanceof RegExp ? q(e, t) : e instanceof Function && !!e(t, ...[...arguments].slice(2));
	}, kt = function(e, t, n) {
		if (!_e[t] && Ft(t) && Ot(ge.tagNameCheck, t)) return !1;
		if (Le && !ze[t]) {
			let t = g(e), r = h(e);
			if (r && t) {
				let i = r.length;
				for (let a = i - 1; a >= 0; --a) {
					let i = e === n ? f(r[a], !0) : r[a];
					t.insertBefore(i, m(e));
				}
			}
		}
		return dt(e), !0;
	}, At = function(e, t, n, r) {
		return e.length === 0 ? t : t === n || t === r ? Fr(t) : t;
	}, jt = function(e, t) {
		return e === t || g(e) !== null ? !1 : (Re && gt(e), !0);
	}, Mt = function(e, n) {
		if (Et(N.beforeSanitizeElements, e, null), jt(e, n)) return !0;
		if (Ct(e)) return dt(e), !0;
		let r = H(C(e));
		if (P = At(N.uponSanitizeElement, P, F, Oe), Et(N.uponSanitizeElement, e, {
			tagName: r,
			allowedTags: P
		}), jt(e, n)) return !0;
		if (Dt(e, r)) return dt(e), !0;
		if (_e[r] || !(ye.tagCheck instanceof Function && ye.tagCheck(r)) && !P[r]) {
			let t = kt(e, r, n);
			return t === !1 && Et(N.afterSanitizeElements, e, null), t;
		}
		if (S(e) === ui.element && !ut(e) || (r === "noscript" || r === "noembed" || r === "noframes") && q(ci, e.innerHTML)) return dt(e), !0;
		if (we && e.nodeType === ui.text) {
			let n = xt(e.textContent);
			e.textContent !== n && (_r(t.removed, { element: e.cloneNode() }), e.textContent = n);
		}
		return Et(N.afterSanitizeElements, e, null), !1;
	}, Nt = function(e, t, r) {
		if (ve[t] || _t(t, e) || Pe && (t === "id" || t === "name") && (r in n || r in nt)) return !1;
		let i = I[t] || ye.attributeCheck instanceof Function && ye.attributeCheck(t, e);
		return xe && q(le, t) || be && q(ue, t) ? !0 : i ? R[t] || q(me, Cr(r, fe, "")) || (t === "src" || t === "xlink:href" || t === "href") && e !== "script" && wr(r, "data:") === 0 && Ve[e] || Se && !q(de, Cr(r, fe, "")) ? !0 : !r : Ft(e) && Ot(ge.tagNameCheck, e) && Ot(ge.attributeNameCheck, t, e) || t === "is" && ge.allowCustomizedBuiltInElements && Ot(ge.tagNameCheck, r);
	}, Pt = Y({}, [
		"annotation-xml",
		"color-profile",
		"font-face",
		"font-face-format",
		"font-face-name",
		"font-face-src",
		"font-face-uri",
		"missing-glyph"
	]), Ft = function(e) {
		return !Pt[br(e)] && q(pe, e);
	}, It = function(e, t, n, r) {
		if (w && typeof u == "object" && typeof u.getAttributeType == "function" && !n) switch (u.getAttributeType(e, t)) {
			case "TrustedHTML": return k(r);
			case "TrustedScriptURL": return te(r);
		}
		return r;
	}, Lt = function(e, n, r, i) {
		try {
			r ? e.setAttributeNS(r, n, i) : e.setAttribute(n, i), Ct(e) ? dt(e) : gr(t.removed);
		} catch {
			mt(n, e);
		}
	}, Rt = function(e) {
		Et(N.beforeSanitizeAttributes, e, null);
		let t = e.attributes;
		if (!t || Ct(e)) return;
		I = At(N.uponSanitizeAttribute, I, he, ke);
		let n = {
			attrName: "",
			attrValue: "",
			keepAttr: !0,
			allowedAttributes: I,
			forceKeepAttr: void 0
		}, r = t.length, i = H(e.nodeName);
		for (; r--;) {
			let a = t[r], o = a.name, s = a.namespaceURI, c = a.value, l = H(o), u = c, d = o === "value" ? u : Tr(u);
			if (n.attrName = l, n.attrValue = d, n.keepAttr = !0, n.forceKeepAttr = void 0, Et(N.uponSanitizeAttribute, e, n), d = n.attrValue, Fe && (l === "id" || l === "name") && wr(d, Ie) !== 0 && (mt(o, e, a), d = Ie + d), Te && q(/((--!?|])>)|<\/(style|script|title|xmp|textarea|noscript|iframe|noembed|noframes)/i, d)) {
				mt(o, e, a);
				continue;
			}
			if (l === "attributename" && Sr(d, "href")) {
				mt(o, e, a);
				continue;
			}
			if (!n.forceKeepAttr) {
				if (!n.keepAttr) {
					mt(o, e, a);
					continue;
				}
				if (!Ce && q(li, d)) {
					mt(o, e, a);
					continue;
				}
				if (we && (d = xt(d)), !Nt(i, l, d)) {
					mt(o, e, a);
					continue;
				}
				d = It(i, l, s, d), d !== u && Lt(e, o, s, d);
			}
		}
		Et(N.afterSanitizeAttributes, e, null);
	}, zt = function(e) {
		let t = null, n = bt(e);
		for (Et(N.beforeSanitizeShadowDOM, e, null); t = n.nextNode();) if (Et(N.uponSanitizeShadowNode, t, null), Mt(t, e), Rt(t), wt(t.content) && zt(t.content), S(t) === ui.element) {
			let e = _(t);
			wt(e) && (Bt(e), zt(e));
		}
		Et(N.afterSanitizeShadowDOM, e, null);
	}, Bt = function(e) {
		let t = [{
			node: e,
			shadow: null
		}];
		for (; t.length > 0;) {
			let e = t.pop();
			if (e.shadow) {
				zt(e.shadow);
				continue;
			}
			let n = e.node, r = S(n) === ui.element, i = h(n);
			if (i) for (let e = i.length - 1; e >= 0; --e) t.push({
				node: i[e],
				shadow: null
			});
			if (r) {
				let e = b ? b(n) : null;
				if (typeof e == "string" && H(e) === "template") {
					let e = n.content;
					wt(e) && t.push({
						node: e,
						shadow: null
					});
				}
			}
			if (r) {
				let e = _(n);
				wt(e) && t.push({
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
		if (Je = !e, Je && (e = "<!-->"), typeof e != "string" && !Tt(e) && (e = Ir(e), typeof e != "string")) throw Mr("dirty is not a string, aborting");
		if (!t.isSupported) return e;
		De ? (P = Oe, I = ke) : it(n), (N.uponSanitizeElement.length > 0 || N.uponSanitizeAttribute.length > 0) && (P = Fr(P)), N.uponSanitizeAttribute.length > 0 && (I = Fr(I)), t.removed = [];
		let c = Re && typeof e != "string" && Tt(e);
		if (c) {
			vt(e);
			let t = C(e);
			if (typeof t == "string") {
				let n = H(t);
				if (!P[n] || _e[n]) throw pt(e), Mr("root node is forbidden and cannot be sanitized in-place");
			}
			if (Ct(e)) throw pt(e), Mr("root node is clobbered and cannot be sanitized in-place");
			try {
				Bt(e);
			} catch (t) {
				throw pt(e), t;
			}
		} else if (Tt(e)) i = yt("<!---->"), a = i.ownerDocument.importNode(e, !0), a.nodeType === ui.element && a.nodeName === "BODY" || a.nodeName === "HTML" ? i = a : i.appendChild(a), Bt(a);
		else {
			if (!je && !we && !Ee && e.indexOf("<") === -1) return w && Ne ? k(e) : e;
			if (i = yt(e), !i) return je ? null : Ne ? T : "";
		}
		i && Ae && dt(i.firstChild);
		let l = c ? e : i;
		try {
			let e = bt(l);
			for (; o = e.nextNode();) Mt(o, l), Rt(o), wt(o.content) && zt(o.content);
		} catch (n) {
			throw c && (pt(e), mr(t.removed, (e) => {
				e.element && gt(e.element);
			})), n;
		}
		if (c) return mr(t.removed, (e) => {
			e.element && gt(e.element);
		}), we && St(e), e;
		if (je) {
			if (we && St(i), Me) for (s = j.call(i.ownerDocument); i.firstChild;) s.appendChild(i.firstChild);
			else s = i;
			return (I.shadowroot || I.shadowrootmode) && (s = M.call(r, s, !0)), s;
		}
		let u = Ee ? i.outerHTML : i.innerHTML;
		return Ee && P["!doctype"] && i.ownerDocument && i.ownerDocument.doctype && i.ownerDocument.doctype.name && q(ii, i.ownerDocument.doctype.name) && (u = "<!DOCTYPE " + i.ownerDocument.doctype.name + ">\n" + u), we && (u = xt(u)), w && Ne ? k(u) : u;
	}, t.setConfig = function() {
		let e = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : {};
		it(e), De = !0, Oe = P, ke = I;
	}, t.clearConfig = function() {
		tt = null, De = !1, Oe = null, ke = null, w = E, T = "";
	}, t.isValidAttribute = function(e, t, n) {
		tt || it({});
		let r = H(e), i = H(t);
		return Nt(r, i, n);
	}, t.addHook = function(e, t) {
		typeof t == "function" && Ar(N, e) && _r(N[e], t);
	}, t.removeHook = function(e, t) {
		if (Ar(N, e)) {
			if (t !== void 0) {
				let n = hr(N[e], t);
				return n === -1 ? void 0 : vr(N[e], n, 1)[0];
			}
			return gr(N[e]);
		}
	}, t.removeHooks = function(e) {
		Ar(N, e) && (N[e] = []);
	}, t.removeAllHooks = function() {
		N = gi();
	}, t;
}
var bi = yi();
//#endregion
//#region node_modules/.pnpm/marked@18.0.10/node_modules/marked/lib/marked.esm.js
function xi() {
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
var Si = xi();
function Ci(e) {
	Si = e;
}
var wi = { exec: () => null };
function Ti(e) {
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
var Ei = ((e = "") => {
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
	nextBulletRegex: Ti((e) => RegExp(`^ {0,${e}}(?:[*+-]|\\d{1,9}[.)])((?:[ 	][^\\n]*)?(?:\\n|$))`)),
	hrRegex: Ti((e) => RegExp(`^ {0,${e}}((?:- *){3,}|(?:_ *){3,}|(?:\\* *){3,})(?:\\n+|$)`)),
	fencesBeginRegex: Ti((e) => RegExp(`^ {0,${e}}(?:\`\`\`|~~~)`)),
	headingBeginRegex: Ti((e) => RegExp(`^ {0,${e}}#`)),
	htmlBeginRegex: Ti((e) => RegExp(`^ {0,${e}}<(?:[a-z].*>|!--)`, "i")),
	blockquoteBeginRegex: Ti((e) => RegExp(`^ {0,${e}}>`))
}, Di = /^(?:[ \t]*(?:\n|$))+/, Oi = /^((?: {4}| {0,3}\t)[^\n]+(?:\n(?:[ \t]*(?:\n|$))*)?)+/, ki = /^ {0,3}(`{3,}(?=[^`\n]*(?:\n|$))|~{3,})([^\n]*)(?:\n|$)(?:|([\s\S]*?)(?:\n|$))(?: {0,3}\1[~`]* *(?=\n|$)|$)/, Ai = /^ {0,3}((?:-[\t ]*){3,}|(?:_[ \t]*){3,}|(?:\*[ \t]*){3,})(?:\n+|$)/, ji = /^ {0,3}(#{1,6})(?=\s|$)(.*)(?:\n+|$)/, Mi = / {0,3}(?:[*+-]|\d{1,9}[.)])/, Ni = /^(?!bull |blockCode|fences|blockquote|heading|html|table)((?:.|\n(?!\s*?\n|bull |blockCode|fences|blockquote|heading|html|table))+?)\n {0,3}(=+|-+) *(?:\n+|$)/, Pi = X(Ni).replace(/bull/g, Mi).replace(/blockCode/g, /(?: {4}| {0,3}\t)/).replace(/fences/g, / {0,3}(?:`{3,}|~{3,})/).replace(/blockquote/g, / {0,3}>/).replace(/heading/g, / {0,3}#{1,6}(?:\s|$)/).replace(/html/g, / {0,3}<[^\n>]+>\n/).replace(/\|table/g, "").getRegex(), Fi = X(Ni).replace(/bull/g, Mi).replace(/blockCode/g, /(?: {4}| {0,3}\t)/).replace(/fences/g, / {0,3}(?:`{3,}|~{3,})/).replace(/blockquote/g, / {0,3}>/).replace(/heading/g, / {0,3}#{1,6}(?:\s|$)/).replace(/html/g, / {0,3}<[^\n>]+>\n/).replace(/table/g, / {0,3}\|?(?:[:\- ]*\|)+[\:\- ]*\n/).getRegex(), Ii = /^([^\n]+(?:\n(?!hr|heading|lheading|blockquote|fences|list|html|table|[ \t]+\n)[^\n]+)*)/, Li = /^[^\n]+/, Ri = /(?!\s*\])(?:\\[\s\S]|[^\[\]\\])+/, zi = X(/^ {0,3}\[(label)\]: *(?:\n[ \t]*)?([^<\s][^\s]*|<.*?>)(?:(?: +(?:\n[ \t]*)?| *\n[ \t]*)(title))? *(?:\n+|$)/).replace("label", Ri).replace("title", /(?:"(?:\\"?|[^"\\])*"|'[^'\n]*(?:\n[^'\n]+)*\n?'|\([^()]*\))/).getRegex(), Bi = X(/^(bull)([ \t][^\n]*?)?(?:\n|$)/).replace(/bull/g, Mi).getRegex(), Vi = "address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|frameset|h[1-6]|head|header|hr|html|iframe|legend|li|link|main|menu|menuitem|meta|nav|noframes|ol|optgroup|option|p|param|search|section|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul", Hi = /<!--(?:-?>|[\s\S]*?(?:-->|$))/, Ui = X("^ {0,3}(?:<(script|pre|style|textarea)[\\s>][\\s\\S]*?(?:</\\1>[^\\n]*\\n*|$)|comment[^\\n]*(\\n+|$)|<\\?[\\s\\S]*?(?:\\?>[^\\n]*\\n*|$)|<![A-Z][\\s\\S]*?(?:>[^\\n]*\\n*|$)|<!\\[CDATA\\[[\\s\\S]*?(?:\\]\\]>[^\\n]*\\n*|$)|</?(tag)(?: +|\\n|/?>)[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$)|<(?!script|pre|style|textarea)([a-z][\\w-]*)(?:attribute)*? */?>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$)|</(?!script|pre|style|textarea)[a-z][\\w-]*\\s*>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$))", "i").replace("comment", Hi).replace("tag", Vi).replace("attribute", / +[a-zA-Z:_][\w.:-]*(?: *= *"[^"\n]*"| *= *'[^'\n]*'| *= *[^\s"'=<>`]+)?/).getRegex(), Wi = (e) => X(Ii).replace("hr", Ai).replace("heading", " {0,3}#{1,6}(?:\\s|$)").replace("|lheading", "").replace("|table", "").replace("blockquote", " {0,3}>").replace("fences", " {0,3}(?:`{3,}(?=[^`\\n]*(?:\\n|$))|~~~)[^\\n]*(?:\\n|$)").replace("list", e).replace("html", "</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag", Vi).getRegex(), Gi = Wi(/ {0,3}(?:[*+-]|1[.)])[ \t]+[^ \t\n]/), Ki = Wi(/ {0,3}(?:[*+-]|\d{1,9}[.)])(?:[ \t]|\n|$)/), qi = {
	blockquote: X(/^( {0,3}> ?(paragraph|[^\n]*)(?:\n|$))+/).replace("paragraph", Ki).getRegex(),
	code: Oi,
	def: zi,
	fences: ki,
	heading: ji,
	hr: Ai,
	html: Ui,
	lheading: Pi,
	list: Bi,
	newline: Di,
	paragraph: Gi,
	table: wi,
	text: Li
}, Ji = X("^ *([^\\n ].*)\\n {0,3}((?:\\| *)?:?-+:? *(?:\\| *:?-+:? *)*(?:\\| *)?)(?:\\n((?:(?! *\\n|hr|heading|blockquote|code|fences|list|html).*(?:\\n|$))*)\\n*|$)").replace("hr", Ai).replace("heading", " {0,3}#{1,6}(?:\\s|$)").replace("blockquote", " {0,3}>").replace("code", "(?: {4}| {0,3}	)[^\\n]").replace("fences", " {0,3}(?:`{3,}(?=[^`\\n]*(?:\\n|$))|~~~)[^\\n]*(?:\\n|$)").replace("list", " {0,3}(?:[*+-]|1[.)])[ \\t]").replace("html", "</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag", Vi).getRegex(), Yi = {
	...qi,
	lheading: Fi,
	table: Ji,
	paragraph: X(Ii).replace("hr", Ai).replace("heading", " {0,3}#{1,6}(?:\\s|$)").replace("|lheading", "").replace("table", Ji).replace("blockquote", " {0,3}>").replace("fences", " {0,3}(?:`{3,}(?=[^`\\n]*(?:\\n|$))|~~~)[^\\n]*(?:\\n|$)").replace("list", " {0,3}(?:[*+-]|1[.)])[ \\t]+[^ \\t\\n]").replace("html", "</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag", Vi).getRegex()
}, Xi = {
	...qi,
	html: X("^ *(?:comment *(?:\\n|\\s*$)|<(tag)[\\s\\S]+?</\\1> *(?:\\n{2,}|\\s*$)|<tag(?:\"[^\"]*\"|'[^']*'|\\s[^'\"/>\\s]*)*?/?> *(?:\\n{2,}|\\s*$))").replace("comment", Hi).replace(/tag/g, "(?!(?:a|em|strong|small|s|cite|q|dfn|abbr|data|time|code|var|samp|kbd|sub|sup|i|b|u|mark|ruby|rt|rp|bdi|bdo|span|br|wbr|ins|del|img)\\b)\\w+(?!:|[^\\w\\s@]*@)\\b").getRegex(),
	def: /^ *\[([^\]]+)\]: *<?([^\s>]+)>?(?: +(["(][^\n]+[")]))? *(?:\n+|$)/,
	heading: /^(#{1,6})(.*)(?:\n+|$)/,
	fences: wi,
	lheading: /^(.+?)\n {0,3}(=+|-+) *(?:\n+|$)/,
	paragraph: X(Ii).replace("hr", Ai).replace("heading", " *#{1,6} *[^\n]").replace("lheading", Pi).replace("|table", "").replace("blockquote", " {0,3}>").replace("|fences", "").replace("|list", "").replace("|html", "").replace("|tag", "").getRegex()
}, Zi = /^\\([!"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])/, Qi = /^(`+)([^`]|[^`][\s\S]*?[^`])\1(?!`)/, $i = /^( {2,}|\\)\n(?!\s*$)/, ea = /^(`+|[^`])(?:(?= {2,}\n)|[\s\S]*?(?:(?=[\\<!\[`*_]|\b_|$)|[^ ](?= {2,}\n)))/, ta = /[\p{P}\p{S}]/u, na = /[\s\p{P}\p{S}]/u, ra = /[^\s\p{P}\p{S}]/u, ia = X(/^((?![*_])punctSpace)/, "u").replace(/punctSpace/g, na).getRegex(), aa = /[\p{Pi}\p{Ps}"']/u, oa = /(?!~)[\p{P}\p{S}]/u, sa = /(?!~)[\s\p{P}\p{S}]/u, ca = /(?:[^\s\p{P}\p{S}]|~)/u, la = X(/link|precode-code|html/, "g").replace("link", /\[(?:[^\[\]`]|(?<a>`+)[^`]+\k<a>(?!`))*?\]\((?:\\[\s\S]|[^\\\(\)]|\((?:\\[\s\S]|[^\\\(\)])*\))*\)/).replace("precode-", Ei ? "(?<!`)()" : "(^^|[^`])").replace("code", /(?<b>`+)[^`]+\k<b>(?!`)/).replace("html", /<(?! )[^<>]*?>/).getRegex(), ua = /^(?:\*+(?:((?!\*)punct)|([^\s*]))?)|^_+(?:((?!_)punct)|([^\s_]))?/, da = X(ua, "u").replace(/punct/g, ta).getRegex(), fa = X(ua, "u").replace(/punct/g, oa).getRegex(), pa = X(/^(?:\*+(?:((?!\*)(?!openQuote)punct)|([^\s*]))?)|^_+(?:((?!_)(?!openQuote)punct)|([^\s_]))?/, "u").replace(/openQuote/g, aa).replace(/punct/g, ta).getRegex(), ma = "^[^_*]*?__[^_*]*?\\*[^_*]*?(?=__)|[^*]+(?=[^*])|(?!\\*)punct(\\*+)(?=[\\s]|$)|notPunctSpace(\\*+)(?!\\*)(?=punctSpace|$)|(?!\\*)punctSpace(\\*+)(?=notPunctSpace)|[\\s](\\*+)(?!\\*)(?=punct)|(?!\\*)punct(\\*+)(?!\\*)(?=punct)|notPunctSpace(\\*+)(?=notPunctSpace)", ha = X(ma, "gu").replace(/notPunctSpace/g, ra).replace(/punctSpace/g, na).replace(/punct/g, ta).getRegex(), ga = X(ma, "gu").replace(/notPunctSpace/g, ca).replace(/punctSpace/g, sa).replace(/punct/g, oa).getRegex(), _a = X("^[^_*]*?__[^_*]*?\\*[^_*]*?(?=__)|[^*]+(?=[^*])|(?!\\*)punct(\\*+)(?=[\\s]|$)|notPunctSpace(\\*+)(?!\\*)(?=punctSpace|$)|(?!\\*)[\\s](\\*+)(?=notPunctSpace)|[\\s](\\*+)(?!\\*)(?=punct)|(?!\\*)punct(\\*+)(?!\\*)(?=punct)|(?:(?!\\*)punct|notPunctSpace)(\\*+)(?!\\*)(?=notPunctSpace)", "gu").replace(/notPunctSpace/g, ra).replace(/punctSpace/g, na).replace(/punct/g, ta).getRegex(), va = X("^[^_*]*?\\*\\*[^_*]*?_[^_*]*?(?=\\*\\*)|[^_]+(?=[^_])|(?!_)punct(_+)(?=[\\s]|$)|notPunctSpace(_+)(?!_)(?=punctSpace|$)|(?!_)punctSpace(_+)(?=notPunctSpace)|[\\s](_+)(?!_)(?=punct)|(?!_)punct(_+)(?!_)(?=punct)", "gu").replace(/notPunctSpace/g, ra).replace(/punctSpace/g, na).replace(/punct/g, ta).getRegex(), ya = X("^[^_*]*?\\*\\*[^_*]*?_[^_*]*?(?=\\*\\*)|[^_]+(?=[^_])|(?!_)punct(_+)(?=[\\s]|$)|notPunctSpace(_+)(?!_)(?=punctSpace|$)|(?!_)[\\s](_+)(?=notPunctSpace)|[\\s](_+)(?!_)(?=punct)|(?!_)punct(_+)(?!_)(?=punct)|(?:(?!_)punct|notPunctSpace)(_+)(?!_)(?=notPunctSpace)", "gu").replace(/notPunctSpace/g, ra).replace(/punctSpace/g, na).replace(/punct/g, ta).getRegex(), ba = X(/^~~?(?:((?!~)punct)|[^\s~])/, "u").replace(/punct/g, ta).getRegex(), xa = X("^[^~]+(?=[^~])|(?!~)punct(~~?)(?=[\\s]|$)|notPunctSpace(~~?)(?!~)(?=punctSpace|$)|(?!~)punctSpace(~~?)(?=notPunctSpace)|[\\s](~~?)(?!~)(?=punct)|(?!~)punct(~~?)(?!~)(?=punct)|notPunctSpace(~~?)(?=notPunctSpace)", "gu").replace(/notPunctSpace/g, ra).replace(/punctSpace/g, na).replace(/punct/g, ta).getRegex(), Sa = X(/\\(punct)/, "gu").replace(/punct/g, ta).getRegex(), Ca = X(/^<(scheme:[^\s\x00-\x1f<>]*|email)>/).replace("scheme", /[a-zA-Z][a-zA-Z0-9+.-]{1,31}/).replace("email", /[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+(@)[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+(?![-_])/).getRegex(), wa = X(Hi).replace("(?:-->|$)", "-->").getRegex(), Ta = X("^comment|^</[a-zA-Z][\\w:-]*\\s*>|^<[a-zA-Z][\\w-]*(?:attribute)*?\\s*/?>|^<\\?[\\s\\S]*?\\?>|^<![a-zA-Z]+\\s[\\s\\S]*?>|^<!\\[CDATA\\[[\\s\\S]*?\\]\\]>").replace("comment", wa).replace("attribute", /\s+[a-zA-Z:_][\w.:-]*(?:\s*=\s*"[^"]*"|\s*=\s*'[^']*'|\s*=\s*[^\s"'=<>`]+)?/).getRegex(), Ea = /(?:\[(?:\\[\s\S]|[^\[\]\\])*\]|\\[\s\S]|`+(?!`)[^`]*?`+(?!`)|``+(?=\])|[^\[\]\\`])*?/, Da = X(/^!?\[(label)\]\(\s*(href)(?:(?:[ \t]+(?:\n[ \t]*)?|\n[ \t]*)(title))?\s*\)/).replace("label", Ea).replace("href", /<(?:\\.|[^\n<>\\])+>|[^ \t\n\x00-\x1f]+|(?=\))/).replace("title", /"(?:\\"?|[^"\\])*"|'(?:\\'?|[^'\\])*'|\((?:\\\)?|[^)\\])*\)/).getRegex(), Oa = X(/^!?\[(label)\]\[(ref)\]/).replace("label", Ea).replace("ref", Ri).getRegex(), ka = X(/^!?\[(ref)\](?:\[\])?/).replace("ref", Ri).getRegex(), Aa = X("reflink|nolink(?!\\()", "g").replace("reflink", Oa).replace("nolink", ka).getRegex(), ja = /[hH][tT][tT][pP][sS]?|[fF][tT][pP]/, Ma = {
	_backpedal: wi,
	anyPunctuation: Sa,
	autolink: Ca,
	blockSkip: la,
	br: $i,
	code: Qi,
	del: wi,
	delLDelim: wi,
	delRDelim: wi,
	emStrongLDelim: da,
	emStrongRDelimAst: ha,
	emStrongRDelimUnd: va,
	escape: Zi,
	link: Da,
	nolink: ka,
	punctuation: ia,
	reflink: Oa,
	reflinkSearch: Aa,
	tag: Ta,
	text: ea,
	url: wi
}, Na = {
	...Ma,
	emStrongLDelim: pa,
	emStrongRDelimAst: _a,
	emStrongRDelimUnd: ya,
	link: X(/^!?\[(label)\]\((.*?)\)/).replace("label", Ea).getRegex(),
	reflink: X(/^!?\[(label)\]\s*\[([^\]]*)\]/).replace("label", Ea).getRegex()
}, Pa = {
	...Ma,
	emStrongRDelimAst: ga,
	emStrongLDelim: fa,
	delLDelim: ba,
	delRDelim: xa,
	url: X(/^((?:protocol):\/\/|www\.)(?:[a-zA-Z0-9\-]+\.?)+[^\s<]*|^email/).replace("protocol", ja).replace("email", /[A-Za-z0-9._+-]+(@)[a-zA-Z0-9-_]+(?:\.[a-zA-Z0-9-_]*[a-zA-Z0-9])+(?![-_])/).getRegex(),
	_backpedal: /(?:[^?!.,:;*_'"~()&]+|\([^)]*\)|&(?![a-zA-Z0-9]+;$)|[?!.,:;*_'"~)]+(?!$))+/,
	del: /^(~~?)(?=[^\s~])((?:\\[\s\S]|[^\\])*?(?:\\[\s\S]|[^\s~\\]))\1(?=[^~]|$)/,
	text: X(/^(`+|~+|[^`~])(?:(?=[`~])|(?= {2,}\n)|(?=[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@)|[\s\S]*?(?:(?=[\\<!\[`*~_]|\b_|protocol:\/\/|www\.|$)|[^ ](?= {2,}\n)|[^a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-](?=[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@)))/).replace("protocol", ja).getRegex()
}, Fa = {
	...Pa,
	br: X($i).replace("{2,}", "*").getRegex(),
	text: X(Pa.text).replace("\\b_", "\\b_| {2,}\\n").replace(/\{2,\}/g, "*").getRegex()
}, Ia = {
	normal: qi,
	gfm: Yi,
	pedantic: Xi
}, La = {
	normal: Ma,
	gfm: Pa,
	breaks: Fa,
	pedantic: Na
}, Ra = {
	"&": "&amp;",
	"<": "&lt;",
	">": "&gt;",
	"\"": "&quot;",
	"'": "&#39;"
}, za = (e) => Ra[e];
function Ba(e, t) {
	if (t) {
		if (Z.escapeTest.test(e)) return e.replace(Z.escapeReplace, za);
	} else if (Z.escapeTestNoEncode.test(e)) return e.replace(Z.escapeReplaceNoEncode, za);
	return e;
}
function Va(e) {
	try {
		e = encodeURI(e).replace(Z.percentDecode, "%");
	} catch {
		return null;
	}
	return e;
}
function Ha(e, t) {
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
function Ua(e, t, n) {
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
function Wa(e) {
	let t = e.split("\n"), n = t.length - 1;
	for (; n >= 0 && Z.blankLine.test(t[n]);) n--;
	return t.length - n <= 2 ? e : t.slice(0, n + 1).join("\n");
}
function Ga(e, t) {
	if (e.indexOf(t[1]) === -1) return -1;
	let n = 0;
	for (let r = 0; r < e.length; r++) if (e[r] === "\\") r++;
	else if (e[r] === t[0]) n++;
	else if (e[r] === t[1] && (n--, n < 0)) return r;
	return n > 0 ? -2 : -1;
}
function Ka(e, t = 0) {
	let n = t, r = "";
	for (let t of e) if (t === "	") {
		let e = 4 - n % 4;
		r += " ".repeat(e), n += e;
	} else r += t, n++;
	return r;
}
function qa(e, t, n, r, i) {
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
function Ja(e, t, n) {
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
var Ya = class {
	options;
	rules;
	lexer;
	constructor(e) {
		this.options = e || Si;
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
			let e = this.options.pedantic ? t[0] : Wa(t[0]);
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
			let e = t[0], n = Ja(e, t[3] || "", this.rules);
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
				let t = Ua(e, "#");
				(this.options.pedantic || !t || this.rules.other.endingSpaceChar.test(t)) && (e = t.trim());
			}
			return {
				type: "heading",
				raw: Ua(t[0], "\n"),
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
			raw: Ua(t[0], "\n")
		};
	}
	blockquote(e) {
		let t = this.rules.block.blockquote.exec(e);
		if (t) {
			let e = Ua(t[0], "\n").split("\n"), n = "", r = "", i = [];
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
				let c = Ka(t[2].split("\n", 1)[0], t[1].length), l = e.split("\n", 1)[0], u = !c.trim(), d = 0;
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
			let e = Wa(t[0]);
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
				raw: Ua(t[0], "\n"),
				href: n,
				title: r
			};
		}
	}
	table(e) {
		let t = this.rules.block.table.exec(e);
		if (!t || !this.rules.other.tableDelimiter.test(t[2])) return;
		let n = Ha(t[1]), r = t[2].replace(this.rules.other.tableAlignChars, "").split("|"), i = t[3]?.trim() ? t[3].replace(this.rules.other.tableRowBlankLine, "").split("\n") : [], a = {
			type: "table",
			raw: Ua(t[0], "\n"),
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
			for (let e of i) a.rows.push(Ha(e, a.header.length).map((e, t) => ({
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
				raw: Ua(t[0], "\n"),
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
				let t = Ua(e.slice(0, -1), "\\");
				if ((e.length - t.length) % 2 == 0) return;
			} else {
				let e = Ga(t[2], "()");
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
			return n = n.trim(), this.rules.other.startAngleBracket.test(n) && (n = this.options.pedantic && !this.rules.other.endAngleBracket.test(e) ? n.slice(1) : n.slice(1, -1)), qa(t, {
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
			return qa(n, e, n[0], this.lexer, this.rules);
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
}, Xa = class e {
	tokens;
	options;
	state;
	inlineQueue;
	tokenizer;
	constructor(e) {
		this.tokens = [], this.tokens.links = Object.create(null), this.options = e || Si, this.options.tokenizer = this.options.tokenizer || new Ya(), this.tokenizer = this.options.tokenizer, this.tokenizer.options = this.options, this.tokenizer.lexer = this, this.inlineQueue = [], this.state = {
			inLink: !1,
			inRawBlock: !1,
			top: !0
		};
		let t = {
			other: Z,
			block: Ia.normal,
			inline: La.normal
		};
		this.options.pedantic ? (t.block = Ia.pedantic, t.inline = La.pedantic) : this.options.gfm && (t.block = Ia.gfm, t.inline = this.options.breaks ? La.breaks : La.gfm), this.tokenizer.rules = t;
	}
	static get rules() {
		return {
			block: Ia,
			inline: La
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
}, Za = class {
	options;
	parser;
	constructor(e) {
		this.options = e || Si;
	}
	space(e) {
		return "";
	}
	code({ text: e, lang: t, escaped: n }) {
		let r = (t || "").match(Z.notSpaceStart)?.[0], i = e.replace(Z.endingNewline, "") + "\n";
		return r ? "<pre><code class=\"language-" + Ba(r) + "\">" + (n ? i : Ba(i, !0)) + "</code></pre>\n" : "<pre><code>" + (n ? i : Ba(i, !0)) + "</code></pre>\n";
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
		return `<code>${Ba(e, !0)}</code>`;
	}
	br(e) {
		return "<br>";
	}
	del({ tokens: e }) {
		return `<del>${this.parser.parseInline(e)}</del>`;
	}
	link({ href: e, title: t, tokens: n }) {
		let r = this.parser.parseInline(n), i = Va(e);
		if (i === null) return r;
		e = i;
		let a = "<a href=\"" + e + "\"";
		return t && (a += " title=\"" + Ba(t) + "\""), a += ">" + r + "</a>", a;
	}
	image({ href: e, title: t, text: n, tokens: r }) {
		r && (n = this.parser.parseInline(r, this.parser.textRenderer));
		let i = Va(e);
		if (i === null) return Ba(n);
		e = i;
		let a = `<img src="${e}" alt="${Ba(n)}"`;
		return t && (a += ` title="${Ba(t)}"`), a += ">", a;
	}
	text(e) {
		return "tokens" in e && e.tokens ? this.parser.parseInline(e.tokens) : "escaped" in e && e.escaped ? e.text : Ba(e.text);
	}
}, Qa = class {
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
}, $a = class e {
	options;
	renderer;
	textRenderer;
	constructor(e) {
		this.options = e || Si, this.options.renderer = this.options.renderer || new Za(), this.renderer = this.options.renderer, this.renderer.options = this.options, this.renderer.parser = this, this.textRenderer = new Qa();
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
}, eo = class {
	options;
	block;
	constructor(e) {
		this.options = e || Si;
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
		return e ? Xa.lex : Xa.lexInline;
	}
	provideParser(e = this.block) {
		return e ? $a.parse : $a.parseInline;
	}
}, to = class {
	defaults = xi();
	options = this.setOptions;
	parse = this.parseMarkdown(!0);
	parseInline = this.parseMarkdown(!1);
	Parser = $a;
	Renderer = Za;
	TextRenderer = Qa;
	Lexer = Xa;
	Tokenizer = Ya;
	Hooks = eo;
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
				let t = this.defaults.renderer || new Za(this.defaults);
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
				let t = this.defaults.tokenizer || new Ya(this.defaults);
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
				let t = this.defaults.hooks || new eo();
				for (let n in e.hooks) {
					if (!(n in t)) throw Error(`hook '${n}' does not exist`);
					if (["options", "block"].includes(n)) continue;
					let r = n, i = e.hooks[r], a = t[r];
					t[r] = eo.passThroughHooks.has(n) ? (e) => {
						if (this.defaults.async && eo.passThroughHooksRespectAsync.has(n)) return (async () => {
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
		return Xa.lex(e, t ?? this.defaults);
	}
	parser(e, t) {
		return $a.parse(e, t ?? this.defaults);
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
				let n = i.hooks ? await i.hooks.preprocess(t) : t, r = await (i.hooks ? await i.hooks.provideLexer(e) : e ? Xa.lex : Xa.lexInline)(n, i), a = i.hooks ? await i.hooks.processAllTokens(r) : r;
				i.walkTokens && await Promise.all(this.walkTokens(a, i.walkTokens));
				let o = await (i.hooks ? await i.hooks.provideParser(e) : e ? $a.parse : $a.parseInline)(a, i);
				return i.hooks ? await i.hooks.postprocess(o) : o;
			})().catch(a);
			try {
				i.hooks && (t = i.hooks.preprocess(t));
				let n = (i.hooks ? i.hooks.provideLexer(e) : e ? Xa.lex : Xa.lexInline)(t, i);
				i.hooks && (n = i.hooks.processAllTokens(n)), i.walkTokens && this.walkTokens(n, i.walkTokens);
				let r = (i.hooks ? i.hooks.provideParser(e) : e ? $a.parse : $a.parseInline)(n, i);
				return i.hooks && (r = i.hooks.postprocess(r)), r;
			} catch (e) {
				return a(e);
			}
		};
	}
	onError(e, t) {
		return (n) => {
			if (n.message += "\nPlease report this to https://github.com/markedjs/marked.", e) {
				let e = "<p>An error occurred:</p><pre>" + Ba(n.message + "", !0) + "</pre>";
				return t ? Promise.resolve(e) : e;
			}
			if (t) return Promise.reject(n);
			throw n;
		};
	}
}, no = new to();
function Q(e, t) {
	return no.parse(e, t);
}
Q.options = Q.setOptions = function(e) {
	return no.setOptions(e), Q.defaults = no.defaults, Ci(Q.defaults), Q;
}, Q.getDefaults = xi, Q.defaults = Si;
function ro(...e) {
	return no.use(...e), Q.defaults = no.defaults, Ci(Q.defaults), Q;
}
Q.use = ro, Q.walkTokens = function(e, t) {
	return no.walkTokens(e, t);
}, Q.parseInline = no.parseInline, Q.Parser = $a, Q.parser = $a.parse, Q.Renderer = Za, Q.TextRenderer = Qa, Q.Lexer = Xa, Q.lexer = Xa.lex, Q.Tokenizer = Ya, Q.Hooks = eo, Q.parse = Q, Q.options, Q.setOptions, Q.walkTokens, Q.parseInline, $a.parse, Xa.lex;
//#endregion
//#region src/presentation.ts
var io = {
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
	accept: "Continue",
	addContext: "Add context",
	agentName: (e) => e ? `${ao(e)} Agent` : "Agent",
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
	modelSearch: "Search models",
	noMatchingModels: "No matching models",
	back: "Back",
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
		minute: "min",
		hour: "h",
		day: "d",
		week: "w",
		month: "m",
		year: "y"
	}[t]}`,
	sessionActions: (e) => `Actions for ${e}`,
	sessionPhase: (e) => ao(e),
	sessionUntitled: "Untitled session",
	sessions: "Sessions",
	pinned: "Pinned",
	sessionTimeUnknown: "Time unavailable",
	pinSession: "Pin session",
	unpinSession: "Unpin session",
	renameSession: "Rename session",
	archiveSession: "Archive session",
	restoreSession: "Restore session",
	archivedSessions: "Archived",
	defaultWorkspace: "Default workspace",
	turnCompleted: (e) => e === void 0 ? "Completed" : `Completed in ${e >= 60 ? Math.floor(e / 60) + "min " : ""}${e % 60}s`,
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
	usage: (e, t) => `${oo(e)} / ${oo(t)}`,
	you: "You",
	confirmDeleteSession: (e) => `Delete “${e}”?`,
	backToSession: (e) => `Back to ${e}`
};
function ao(e) {
	return e.replaceAll(/[_-]+/g, " ").trim().replaceAll(/(^|\s)\S/g, (e) => e.toUpperCase());
}
function oo(e) {
	return e < 0xe8d4a51000 ? e.toLocaleString() : e.toExponential(2);
}
//#endregion
//#region src/react/clipboard.ts
var so = 1e3;
function co(e) {
	let [t, n] = z(!1), r = V(!1), i = V(void 0), a = V(0);
	return B(() => (a.current += 1, r.current = !1, n(!1), i.current !== void 0 && (window.clearTimeout(i.current), i.current = void 0), () => {
		a.current += 1, r.current = !1, i.current !== void 0 && (window.clearTimeout(i.current), i.current = void 0);
	}), [e]), {
		copied: t,
		copy: $e((o) => {
			if (!e || t || r.current) return;
			let s = a.current;
			r.current = !0, lo(e, o).then((e) => {
				s === a.current && (r.current = !1, e && (n(!0), i.current = window.setTimeout(() => {
					i.current = void 0, n(!1);
				}, so)));
			});
		}, [t, e])
	};
}
async function lo(e, t) {
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
var uo = new Intl.DateTimeFormat(void 0, {
	month: "short",
	day: "numeric"
}), fo = new Intl.DateTimeFormat(void 0, {
	year: "numeric",
	month: "short",
	day: "numeric"
});
function po({ content: e, timestamp: t, clock: n, labels: r }) {
	let i = yo(), { copied: a, copy: o } = co(ho(e)), s = t !== void 0 && Number.isFinite(t) && t >= 0 && !Number.isNaN(new Date(t).valueOf()) ? t : void 0, c = s === void 0 ? null : /* @__PURE__ */ W("time", {
		className: `paui-message__time paui-message__time--${n}`,
		dateTime: new Date(s).toISOString(),
		children: mo(s, i)
	}), l = a ? r.copied : r.copy;
	return /* @__PURE__ */ W("div", {
		className: "paui-message__actions",
		"data-pretty-aui-slot": "message-actions",
		"data-clock": n,
		children: [
			n === "start" ? c : null,
			/* @__PURE__ */ W("button", {
				className: "paui-message__action",
				type: "button",
				"aria-label": l,
				title: l,
				onClick: (e) => o(e.currentTarget),
				children: W(a ? Do : Eo, {})
			}),
			n === "end" ? c : null
		]
	});
}
function mo(e, t = Date.now()) {
	let n = new Date(e), r = new Date(t), i = `${wo(n.getHours())}:${wo(n.getMinutes())}`, a = n.getFullYear() === r.getFullYear();
	return a && n.getMonth() === r.getMonth() && n.getDate() === r.getDate() ? i : `${a ? uo.format(n) : fo.format(n)} ${i}`;
}
function ho(e) {
	return e.flatMap((e) => e.type === "text" && typeof e.text == "string" ? [e.text] : []).join("");
}
var go = So(Date.now()), _o, vo = /* @__PURE__ */ new Set();
function yo() {
	return ut(bo, () => go, () => go);
}
function bo(e) {
	vo.add(e);
	let t = So(Date.now());
	if (t !== go) {
		go = t;
		for (let e of vo) e();
	}
	return vo.size === 1 && xo(), () => {
		vo.delete(e), !vo.size && _o !== void 0 && (window.clearTimeout(_o), _o = void 0);
	};
}
function xo() {
	_o !== void 0 && window.clearTimeout(_o);
	let e = Date.now();
	_o = window.setTimeout(() => {
		_o = void 0, go = So(Date.now());
		for (let e of vo) e();
		vo.size && xo();
	}, Co(e));
}
function So(e) {
	let t = new Date(e);
	return t.setHours(0, 0, 0, 0), t.getTime();
}
function Co(e) {
	let t = new Date(e);
	return t.setHours(24, 0, 0, 0), Math.max(1, t.getTime() - e);
}
function wo(e) {
	return String(e).padStart(2, "0");
}
function To({ children: e }) {
	return /* @__PURE__ */ W("svg", {
		viewBox: "0 0 16 16",
		"aria-hidden": "true",
		focusable: "false",
		children: e
	});
}
function Eo() {
	return /* @__PURE__ */ W(To, { children: [/* @__PURE__ */ W("rect", {
		x: "2.5",
		y: "4.5",
		width: "9",
		height: "9",
		rx: "2"
	}), /* @__PURE__ */ W("path", { d: "M5 4V3.5a2 2 0 0 1 2-2h5.5a2 2 0 0 1 2 2V9a2 2 0 0 1-2 2H12" })] });
}
function Do() {
	return /* @__PURE__ */ W(To, { children: /* @__PURE__ */ W("path", { d: "m3 8.25 3.15 3.15L13 4.55" }) });
}
//#endregion
//#region src/react/tool-block-model.ts
var Oo = 1e5;
function ko(e) {
	return No(e) ?? jo(e) ?? Mo(e) ?? Po(e);
}
function Ao(e) {
	return (typeof e == "string" ? e : (() => {
		try {
			return JSON.stringify(e, null, 2) ?? String(e);
		} catch {
			return String(e);
		}
	})()).slice(0, Oo);
}
function jo(e) {
	let t = e.kind?.toLowerCase();
	if (t !== "execute" && t !== "bash" && t !== "shell" && t !== "terminal" || !Zo(e.rawInput)) return;
	let n = Yo(e.rawInput.command, e.rawInput.cmd);
	if (!n?.trim()) return;
	let r = Yo(e.rawInput.cwd, e.rawInput.workdir), { text: i, remaining: a } = Io(e.content), o = Zo(e.rawOutput) ? e.rawOutput : void 0, s = i ?? Yo(o?.output, o?.error) ?? (typeof e.rawOutput == "string" ? e.rawOutput : ""), c = e.status === "pending" || e.status === "in_progress";
	return {
		kind: "terminal",
		command: n,
		...r ? { cwd: r } : {},
		output: s,
		displayOutput: Xo(s),
		running: c,
		failed: e.status === "failed" || e.status === "cancelled",
		supplementary: a
	};
}
function Mo(e) {
	if (e.kind?.toLowerCase() !== "read" || e.status !== "completed") return;
	let t = Zo(e.rawInput) ? e.rawInput : void 0, n = Zo(e.rawOutput) ? e.rawOutput : void 0, r = Zo(n?.metadata) ? n.metadata : void 0, i = Zo(r?.display) ? r.display : void 0;
	if (i?.type === "directory") return;
	let { text: a, remaining: o } = Io(e.content), s = i?.type === "file" && typeof i.text == "string" ? i.text : void 0, c = a ?? s;
	if (c === void 0) return;
	let l = i?.type === "file", u = Ho(c), d = Uo(u?.text ?? c);
	if (!l && !u && !d) return;
	let f = u?.text ?? c, p = Jo(t?.offset) ?? 1, m = d ?? Wo(f).map((e, t) => ({
		number: p + t,
		text: e
	})), h = Yo(u?.path, t?.filePath, t?.file_path, t?.filepath, t?.path, qo(e)), g = Ko(e.title) ?? h;
	if (g) return {
		kind: "read",
		label: g,
		lines: m,
		copyText: m.map((e) => e.text).join("\n"),
		supplementary: o
	};
}
function No(e) {
	let t = [], n = [], r = /* @__PURE__ */ new Set(), i = /* @__PURE__ */ new Set(), a = 0, o = 0;
	if (e.content.forEach((e, s) => {
		if (!Zo(e) || e.type !== "diff") return;
		let c = zo(e);
		if (c) {
			r.add(s), i.add(c.path);
			let e = [{
				kind: "meta",
				text: c.path
			}];
			if (c.oldText !== null) for (let t of Go(c.oldText)) e.push({
				kind: "delete",
				text: `- ${t}`
			}), o += 1;
			for (let t of Go(c.newText)) e.push({
				kind: "add",
				text: `+ ${t}`
			}), a += 1;
			t.push(...e), n.push(e.map((e) => e.text).join("\n"));
			return;
		}
		let l = Bo(e);
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
function Po(e) {
	let t = e.rawInput === void 0 ? void 0 : Fo(Ao(e.rawInput));
	if (e.content.length) {
		let n = Lo(e.content);
		return {
			kind: "io",
			...t ? { input: t } : {},
			output: {
				values: e.content,
				copyText: n
			}
		};
	}
	let n = e.rawOutput === void 0 ? void 0 : Fo(Ao(e.rawOutput));
	return {
		kind: "io",
		...t ? { input: t } : {},
		...n ? { output: n } : {}
	};
}
function Fo(e) {
	return {
		text: e,
		copyText: e
	};
}
function Io(e) {
	let t = [], n = [];
	for (let r of e) {
		let e = Ro(r);
		e === void 0 ? n.push(r) : t.push(e);
	}
	return {
		...t.length ? { text: t.join("\n") } : {},
		remaining: n
	};
}
function Lo(e) {
	return e.flatMap((e) => {
		let t = Ro(e);
		return t === void 0 ? [] : [t];
	}).join("\n");
}
function Ro(e) {
	if (!(!Zo(e) || e.type !== "content" || !Zo(e.content))) return e.content.type === "text" && typeof e.content.text == "string" ? e.content.text : void 0;
}
function zo(e) {
	if (!(typeof e.path != "string" || !e.path.trim() || typeof e.newText != "string") && (e.oldText === void 0 || e.oldText === null || typeof e.oldText == "string")) return {
		path: e.path,
		oldText: typeof e.oldText == "string" ? e.oldText : null,
		newText: e.newText
	};
}
function Bo(e) {
	if (!Array.isArray(e.changes)) return;
	let t = e.changes.filter(Zo);
	if (t.length !== e.changes.length) return;
	let n = [];
	for (let e of t) {
		if (typeof e.operation != "string" || !e.operation.trim() || typeof e.path != "string" || !e.path.trim()) return;
		n.push(e.path), typeof e.oldPath == "string" && n.push(e.oldPath);
	}
	let r = typeof e.patch == "string" ? e.patch : Zo(e.patch) && typeof e.patch.text == "string" ? e.patch.text : void 0;
	if (r !== void 0) return {
		rows: r.split(/\r?\n/).map(Vo),
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
function Vo(e) {
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
function Ho(e) {
	let t = /^<path>([^\r\n]*)<\/path>\r?\n<type>file<\/type>\r?\n<content>\r?\n([\s\S]*)\r?\n<\/content>$/.exec(e);
	return t?.[1] !== void 0 && t[2] !== void 0 ? {
		path: t[1],
		text: t[2]
	} : void 0;
}
function Uo(e) {
	let t = Wo(e);
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
function Wo(e) {
	return e ? (e.endsWith("\n") ? e.slice(0, -1) : e).split(/\r?\n/) : [];
}
function Go(e) {
	return e ? Wo(e) : [];
}
function Ko(e) {
	let t = e.trim(), n = t.toLowerCase();
	return t && n !== "read" && n !== "tool" ? t : void 0;
}
function qo(e) {
	return e.locations.find((e) => typeof e.path == "string")?.path;
}
function Jo(e) {
	return typeof e == "number" && Number.isSafeInteger(e) && e > 0 ? e : void 0;
}
function Yo(...e) {
	return e.find((e) => typeof e == "string");
}
function Xo(e) {
	return e.replaceAll(/\u001b\][^\u0007\u001b]*(?:\u0007|\u001b\\)?/g, "").replaceAll(/\u001b\[[\u0030-\u003f]*[\u0020-\u002f]*[\u0040-\u007e]/g, "").replaceAll("\r\n", "\n").replaceAll("\r", "\n").replaceAll(/[\u0000-\u0008\u000b\u000c\u000e-\u001a\u001c-\u001f\u007f]/g, "");
}
function Zo(e) {
	return typeof e == "object" && !!e && !Array.isArray(e);
}
//#endregion
//#region src/react/ToolBlocks.tsx
function Qo({ tool: e, labels: t, renderContent: n }) {
	let r = ko(e);
	switch (r.kind) {
		case "terminal": return /* @__PURE__ */ W(F, { children: [/* @__PURE__ */ W($o, {
			model: r,
			status: e.status,
			labels: t
		}), /* @__PURE__ */ W(as, {
			values: r.supplementary,
			render: n
		})] });
		case "read": return /* @__PURE__ */ W(F, { children: [/* @__PURE__ */ W(es, {
			model: r,
			labels: t
		}), /* @__PURE__ */ W(as, {
			values: r.supplementary,
			render: n
		})] });
		case "diff": return /* @__PURE__ */ W(F, { children: [/* @__PURE__ */ W(ns, {
			model: r,
			labels: t
		}), /* @__PURE__ */ W(as, {
			values: r.supplementary,
			render: n
		})] });
		case "io": return !r.input && !r.output ? /* @__PURE__ */ W("span", {
			className: "paui-muted",
			children: t.tool
		}) : /* @__PURE__ */ W("div", {
			className: "paui-tool-block paui-tool-io",
			"data-tool-block": "io",
			children: [
				r.input ? /* @__PURE__ */ W(is, {
					label: t.toolInput,
					section: r.input,
					labels: t,
					render: n
				}) : null,
				r.input && r.output ? /* @__PURE__ */ W("span", {
					className: "paui-tool-io__divider",
					"aria-hidden": "true"
				}) : null,
				r.output ? /* @__PURE__ */ W(is, {
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
function $o({ model: e, status: t, labels: n }) {
	let r = e.displayOutput.trim().length > 0;
	return /* @__PURE__ */ W("div", {
		className: "paui-tool-block paui-tool-terminal",
		"data-tool-block": "terminal",
		"data-state": e.failed ? "failed" : e.running ? "running" : "completed",
		children: [/* @__PURE__ */ W("div", {
			className: "paui-tool-terminal__header",
			children: [/* @__PURE__ */ W("div", {
				className: "paui-tool-terminal__prompt",
				children: [/* @__PURE__ */ W("span", {
					className: "paui-sr-only",
					children: t
				}), ls(e.command).map((t, n) => /* @__PURE__ */ W("div", {
					className: "paui-tool-terminal__prompt-line",
					children: [
						n === 0 ? /* @__PURE__ */ W("span", {
							className: "paui-tool-terminal__state",
							"aria-hidden": "true"
						}) : null,
						/* @__PURE__ */ W("span", {
							className: "paui-tool-terminal__cwd",
							children: n === 0 && e.cwd ? e.cwd : "$"
						}),
						/* @__PURE__ */ W("span", {
							className: "paui-tool-terminal__command",
							children: t
						})
					]
				}, n))]
			}), !e.running && r ? /* @__PURE__ */ W(os, {
				text: e.output,
				labels: n
			}) : null]
		}), e.running ? null : r ? /* @__PURE__ */ W("pre", {
			className: "paui-tool-terminal__output",
			children: e.displayOutput
		}) : /* @__PURE__ */ W("div", {
			className: "paui-tool-block__empty",
			children: n.toolNoOutput
		})]
	});
}
function es({ model: e, labels: t }) {
	let [n, r] = z(!1), i = cs(e.lines, n);
	return /* @__PURE__ */ W("div", {
		className: "paui-tool-block paui-tool-read",
		"data-tool-block": "read",
		children: [/* @__PURE__ */ W("div", {
			className: "paui-tool-block__banner",
			children: [/* @__PURE__ */ W("span", {
				className: "paui-tool-block__label",
				children: e.label
			}), e.copyText ? /* @__PURE__ */ W(os, {
				text: e.copyText,
				labels: t
			}) : null]
		}), /* @__PURE__ */ W("div", {
			className: "paui-tool-read__body",
			children: [
				/* @__PURE__ */ W(ts, { lines: i.head }),
				i.hidden > 0 ? /* @__PURE__ */ W(ss, {
					expanded: n,
					hidden: i.hidden,
					labels: t,
					onClick: () => r((e) => !e)
				}) : null,
				/* @__PURE__ */ W(ts, { lines: i.tail })
			]
		})]
	});
}
function ts({ lines: e }) {
	return e.map((e) => /* @__PURE__ */ W("div", {
		className: "paui-tool-read__line",
		children: [/* @__PURE__ */ W("span", {
			className: "paui-tool-read__gutter",
			"aria-hidden": "true",
			children: e.number
		}), /* @__PURE__ */ W("span", {
			className: "paui-tool-read__content",
			children: e.text
		})]
	}, e.number));
}
function ns({ model: e, labels: t }) {
	let [n, r] = z(!1), i = cs(e.rows, n);
	return /* @__PURE__ */ W("div", {
		className: "paui-tool-block paui-tool-diff",
		"data-tool-block": "diff",
		children: [
			/* @__PURE__ */ W("div", {
				className: "paui-tool-block__banner paui-tool-diff__banner",
				children: [/* @__PURE__ */ W("span", {
					className: "paui-tool-block__label",
					children: t.changedFiles
				}), /* @__PURE__ */ W(os, {
					text: e.copyText,
					labels: t
				})]
			}),
			/* @__PURE__ */ W("div", {
				className: "paui-tool-diff__body",
				children: [
					/* @__PURE__ */ W(rs, { rows: i.head }),
					i.hidden > 0 ? /* @__PURE__ */ W(ss, {
						expanded: n,
						hidden: i.hidden,
						labels: t,
						onClick: () => r((e) => !e)
					}) : null,
					/* @__PURE__ */ W(rs, { rows: i.tail })
				]
			}),
			/* @__PURE__ */ W("div", {
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
function rs({ rows: e }) {
	return e.map((e, t) => /* @__PURE__ */ W("div", {
		className: "paui-tool-diff__line",
		"data-line-kind": e.kind,
		children: e.text
	}, t));
}
function is({ label: e, section: t, labels: n, render: r, failed: i = !1 }) {
	return /* @__PURE__ */ W("section", {
		className: "paui-tool-io__section",
		"data-error": i || void 0,
		children: [/* @__PURE__ */ W("div", {
			className: "paui-tool-io__section-header",
			children: [/* @__PURE__ */ W("strong", { children: e }), t.copyText ? /* @__PURE__ */ W(os, {
				text: t.copyText,
				labels: n
			}) : null]
		}), /* @__PURE__ */ W("div", {
			className: "paui-tool-io__content",
			children: [t.text === void 0 ? null : /* @__PURE__ */ W("pre", { children: t.text }), t.values?.map(r)]
		})]
	});
}
function as({ values: e, render: t }) {
	return e.length ? /* @__PURE__ */ W("div", {
		className: "paui-tool-supplementary",
		children: e.map(t)
	}) : null;
}
function os({ text: e, labels: t }) {
	let { copied: n, copy: r } = co(e), i = n ? t.copied : t.copy;
	return /* @__PURE__ */ W("button", {
		className: "paui-tool-block__copy",
		type: "button",
		"aria-label": i,
		title: i,
		onClick: (e) => r(e.currentTarget),
		children: i
	});
}
function ss({ expanded: e, hidden: t, labels: n, onClick: r }) {
	return /* @__PURE__ */ W("button", {
		className: "paui-tool-block__fold",
		type: "button",
		"aria-expanded": e,
		onClick: r,
		children: e ? n.toolCollapseLines : n.toolExpandLines(t)
	});
}
function cs(e, t) {
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
function ls(e) {
	return (e.endsWith("\n") ? e.slice(0, -1) : e).split("\n");
}
//#endregion
//#region src/react/Chat.tsx
var us = Le(void 0), ds = /* @__PURE__ */ new WeakMap(), fs = 0, ps = {
	draft: zt,
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
}, ms = {
	setDraft() {},
	appendDraft() {},
	addDraftImages() {},
	removeDraftImage() {},
	selectCommand() {},
	recoverDraft() {},
	refreshComposerActions() {},
	getComposerActions: () => [],
	async runComposerAction() {
		return !1;
	},
	sendDraft() {
		throw Error("The chat session is still connecting");
	},
	ready: new Promise(() => void 0),
	getSnapshot: () => ps,
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
function hs(e) {
	let t = et(us);
	if (!t) throw Error(`pretty-aui: ${e} must be rendered inside a ChatRoot.`);
	return t;
}
function gs(e) {
	return /* @__PURE__ */ W(_s, {
		...e,
		children: [
			/* @__PURE__ */ W(Cs, {}),
			/* @__PURE__ */ W(ws, {}),
			/* @__PURE__ */ W(Ts, {}),
			/* @__PURE__ */ W(Zs, {})
		]
	});
}
function _s(e) {
	if ("controller" in e) {
		let { controller: t, ...n } = e;
		return /* @__PURE__ */ W(ys, {
			...n,
			controller: t
		}, gc(t));
	}
	let { options: t, ...n } = e;
	return /* @__PURE__ */ W(vs, {
		...n,
		options: t
	});
}
function vs(e) {
	let { options: t, ...n } = e, r = V(t), [i, a] = z();
	return B(() => {
		let e = gn(r.current);
		return a(e), () => {
			e.destroy();
		};
	}, []), i ? /* @__PURE__ */ W(ys, {
		...n,
		controller: i
	}, gc(i)) : /* @__PURE__ */ W(ys, {
		...n,
		controller: ms
	}, "connecting");
}
function ys(e) {
	let { controller: t } = e, n = ut($e((e) => vc(t, e), [t]), $e(() => t.getSnapshot(), [t]), $e(() => t.getSnapshot(), [t])), r = Qe(() => ({
		...io,
		...e.labels
	}), [e.labels]), i = H().replaceAll(":", ""), [a, o] = z(), s = $e((e) => {
		o(void 0), e().catch((e) => {
			o(e instanceof Error ? e.message : String(e));
		});
	}, []), c = e.colorScheme ?? "system", l = e.surface ?? "inline", u = Qe(() => ({
		controller: t,
		snapshot: n,
		labels: r,
		sessionOrganization: e.sessionOrganization,
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
		e.sessionOrganization,
		e.toolActivityRenderer,
		s,
		n
	]);
	return /* @__PURE__ */ W("section", {
		className: ["pretty-aui", e.className].filter(Boolean).join(" "),
		"data-pretty-aui-slot": "root",
		"data-surface": l,
		"data-scheme": c,
		"data-phase": n.phase,
		style: e.style,
		"aria-label": n.agentName ?? r.assistantName,
		children: /* @__PURE__ */ W(us.Provider, {
			value: u,
			children: e.children
		})
	});
}
var bs = new Intl.DateTimeFormat(void 0, {
	dateStyle: "long",
	timeStyle: "medium"
}), xs = /* @__PURE__ */ new Map();
function Ss(e, t, n) {
	n ? e.set(t, n) : e.delete(t);
}
function Cs() {
	let { controller: e, snapshot: t, labels: n, runAction: r, sessionOrganization: i } = hs("ChatHeader"), [a, o] = z(!1), [s, c] = z(), l = V(null), u = s?.adapter === i ? s : void 0, d = u?.rows ?? xs, f = $e(async () => {
		if (!i || l.current?.adapter === i) return;
		let e = {
			adapter: i,
			writes: /* @__PURE__ */ new Map()
		};
		l.current = e;
		try {
			let t = await e.adapter.list();
			if (l.current !== e) return;
			let n = new Map(t.map((e) => [e.sessionId, e]));
			for (let [t, r] of e.writes) Ss(n, t, r);
			c({
				adapter: e.adapter,
				rows: n
			});
		} catch (t) {
			if (l.current !== e) return;
			c((n) => ({
				adapter: e.adapter,
				rows: n?.adapter === e.adapter ? n.rows : void 0,
				error: t instanceof Error ? t.message : String(t)
			}));
		} finally {
			l.current === e && (l.current = null);
		}
	}, [i]);
	B(() => (f(), () => {
		l.current = null;
	}), [f]);
	let p = u?.rows ? async (e, t) => {
		let n = await u.adapter.patch(e, t), r = l.current;
		r?.adapter === u.adapter && r.writes.set(e.sessionId, n), c((t) => {
			if (!t?.rows || t.adapter !== u.adapter) return t;
			let r = new Map(t.rows);
			return Ss(r, e.sessionId, n), {
				...t,
				rows: r
			};
		});
	} : void 0, m = d.get(t.sessionId ?? "")?.alias || (t.sessionTitle ?? n.sessionUntitled), h = t.sessionTrail.at(-1), g = t.protocolVersion !== void 0 && t.phase !== "connecting" && t.phase !== "auth_required" && t.phase !== "closed" && t.loadedSessions.length < 16;
	return /* @__PURE__ */ W(F, { children: [/* @__PURE__ */ W("header", {
		className: "paui-header",
		"data-pretty-aui-slot": "header",
		children: [/* @__PURE__ */ W("div", {
			className: `paui-identity${h ? " paui-identity--child" : ""}`,
			children: [/* @__PURE__ */ W("span", {
				className: "paui-presence",
				"data-phase": t.phase,
				"aria-hidden": "true"
			}), h ? /* @__PURE__ */ W("div", {
				className: "paui-lineage",
				"data-depth": t.sessionTrail.length,
				children: [
					/* @__PURE__ */ W("button", {
						className: "paui-lineage__back",
						type: "button",
						disabled: t.phase !== "idle",
						"aria-label": n.backToSession(h.title ?? h.sessionId),
						onClick: () => r(() => e.openAncestorSession(h.sessionId)),
						children: /* @__PURE__ */ W(Fc, {})
					}),
					/* @__PURE__ */ W("div", {
						className: "paui-lineage__titles",
						children: [t.sessionTrail.map((n) => {
							let i = n.title ?? n.sessionId;
							return /* @__PURE__ */ W("span", {
								className: "paui-lineage__ancestor",
								children: [/* @__PURE__ */ W("button", {
									type: "button",
									disabled: t.phase !== "idle",
									onClick: () => r(() => e.openAncestorSession(n.sessionId)),
									children: i
								}), /* @__PURE__ */ W("span", {
									"aria-hidden": "true",
									children: "/"
								})]
							}, n.sessionId);
						}), /* @__PURE__ */ W("strong", { children: m })]
					}),
					/* @__PURE__ */ W("span", {
						className: "paui-protocol",
						children: t.protocolVersion ? `ACP v${t.protocolVersion}` : t.phase
					})
				]
			}) : /* @__PURE__ */ W("div", { children: [/* @__PURE__ */ W("strong", { children: m }), /* @__PURE__ */ W("span", {
				className: "paui-protocol",
				children: t.protocolVersion ? `ACP v${t.protocolVersion}` : t.phase
			})] })]
		}), /* @__PURE__ */ W("div", {
			className: "paui-header__actions",
			children: [
				t.usage ? /* @__PURE__ */ W("span", {
					className: "paui-usage",
					children: n.usage(t.usage.used, t.usage.size)
				}) : null,
				t.capabilities.listSessions || i || t.loadedSessions.length > 1 ? /* @__PURE__ */ W("button", {
					className: "paui-icon-button",
					type: "button",
					onClick: () => {
						o(!0), f();
					},
					children: [/* @__PURE__ */ W(wc, {}), /* @__PURE__ */ W("span", {
						className: "paui-sr-only",
						children: n.sessions
					})]
				}) : null,
				/* @__PURE__ */ W("button", {
					className: "paui-icon-button",
					type: "button",
					disabled: !g,
					onClick: () => r(() => e.newSession()),
					children: [/* @__PURE__ */ W(Tc, {}), /* @__PURE__ */ W("span", {
						className: "paui-sr-only",
						children: n.newChat
					})]
				})
			]
		})]
	}), a ? /* @__PURE__ */ W(oc, {
		controller: e,
		snapshot: t,
		labels: n,
		decorations: d,
		organizationError: u?.error,
		updateDecoration: p,
		onClose: () => o(!1)
	}) : null] });
}
function ws() {
	let { snapshot: e, labels: t, toolActivityRenderer: n } = hs("ChatTranscript"), r = V(null), i = V(null), a = V(!0), o = V(0), s = _c(e), c = V(s), l = V(/* @__PURE__ */ new Map()), [u, d] = z(!0), f = $e((e = "auto") => {
		let t = r.current;
		t && (typeof t.scrollTo == "function" ? t.scrollTo({
			top: t.scrollHeight,
			behavior: e
		}) : t.scrollTop = t.scrollHeight, o.current = t.scrollTop, a.current = !0, d(!0));
	}, []), p = $e(() => {
		let e = r.current;
		if (!e) return;
		let t = e.scrollHeight - e.scrollTop - e.clientHeight, n = e.scrollTop < o.current - 1, i = t <= 24 || !n && a.current;
		o.current = e.scrollTop, a.current = i, l.current.set(s, {
			top: e.scrollTop,
			pinned: i
		}), d(i);
	}, [s]);
	Ze(() => {
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
	}, [f, s]), Ze(() => {
		a.current && f();
	}, [
		f,
		e.activities,
		e.historyGap
	]), B(() => {
		let e = i.current;
		if (!e || typeof ResizeObserver > "u") return;
		let t = new ResizeObserver(() => {
			a.current && f();
		});
		return t.observe(e), r.current && t.observe(r.current), () => t.disconnect();
	}, [f]);
	let m = Qe(() => Es(e.activities), [e.activities]), [h, g] = z(() => /* @__PURE__ */ new Map()), _ = h.get(e.sessionId), v = _?.instance === e.sessionInstanceId ? _?.turns : void 0, y = (t) => {
		let n = new Map(h);
		for (let t of n.keys()) t !== e.sessionId && !e.loadedSessions.some((e) => e.sessionId === t) && n.delete(t);
		let r = new Set(m.filter((e) => v?.has(e.id)).map((e) => e.id));
		r.has(t) ? r.delete(t) : r.add(t), r.size ? n.set(e.sessionId, {
			instance: e.sessionInstanceId,
			turns: r
		}) : n.delete(e.sessionId), g(n);
	}, b = e.phase === "running" || e.phase === "awaiting_user" || e.phase === "cancelling";
	return /* @__PURE__ */ W(F, { children: [/* @__PURE__ */ W("main", {
		ref: r,
		className: "paui-body",
		"data-pretty-aui-slot": "transcript",
		tabIndex: 0,
		onScroll: p,
		children: /* @__PURE__ */ W("div", {
			className: "paui-transcript",
			ref: i,
			children: [
				e.historyGap ? /* @__PURE__ */ W("aside", {
					className: "paui-notice",
					role: "status",
					children: [/* @__PURE__ */ W(Zc, {}), /* @__PURE__ */ W("div", { children: [/* @__PURE__ */ W("strong", { children: t.historyGapTitle }), /* @__PURE__ */ W("span", { children: t.historyGap })] })]
				}) : null,
				e.activities.length ? null : /* @__PURE__ */ W("div", {
					className: "paui-empty",
					children: [
						/* @__PURE__ */ W($c, {}),
						/* @__PURE__ */ W("strong", { children: t.emptyTitle }),
						/* @__PURE__ */ W("p", { children: t.emptyDescription })
					]
				}),
				m.map((e, r) => /* @__PURE__ */ W(Ds, {
					turn: e,
					followedByTurn: r < m.length - 1,
					labels: t,
					expanded: v?.has(e.id) ?? !1,
					onToggle: y,
					toolActivityRenderer: n,
					active: b && r === m.length - 1
				}, s + e.id))
			]
		})
	}), u ? null : /* @__PURE__ */ W("div", {
		className: "paui-to-bottom-row",
		children: /* @__PURE__ */ W("button", {
			className: "paui-to-bottom",
			type: "button",
			onClick: () => f("smooth"),
			"aria-label": t.scrollToLatest,
			children: /* @__PURE__ */ W(Pc, {})
		})
	})] });
}
function Ts() {
	let { controller: e, snapshot: t, labels: n, actionError: r, runAction: i } = hs("ChatInteractions"), a = V(null);
	return B(() => {
		if (!t.interactions.length) return;
		let e = a.current;
		if (!e) return;
		let n = cc(e);
		n && e.contains(n) || e.querySelector(uc)?.focus();
	}, [t.interactions.map((e) => e.id).join("\0"), t.interactions.length]), /* @__PURE__ */ W("div", {
		ref: a,
		className: "paui-interactions",
		"data-pretty-aui-slot": "interactions",
		children: [
			t.phase === "auth_required" ? /* @__PURE__ */ W(ac, {}) : null,
			t.interactions.map((t) => t.type === "permission" ? /* @__PURE__ */ W(tc, {
				interaction: t,
				controller: e,
				labels: n
			}, t.id) : /* @__PURE__ */ W(nc, {
				interaction: t,
				controller: e,
				labels: n
			}, t.id)),
			t.error ? /* @__PURE__ */ W("aside", {
				className: "paui-error",
				role: "alert",
				children: [/* @__PURE__ */ W("div", { children: [/* @__PURE__ */ W("strong", { children: n.error }), /* @__PURE__ */ W("span", { children: t.error.message })] }), t.error.retryable ? /* @__PURE__ */ W("button", {
					type: "button",
					onClick: () => i(() => e.reconnect()),
					children: n.retry
				}) : null]
			}) : null,
			r && !t.error ? /* @__PURE__ */ W("aside", {
				className: "paui-error",
				role: "alert",
				children: /* @__PURE__ */ W("div", { children: [/* @__PURE__ */ W("strong", { children: n.error }), /* @__PURE__ */ W("span", { children: r })] })
			}) : null
		]
	});
}
function Es(e) {
	let t = [], n;
	for (let r of e) {
		let e = r.type === "message" && r.role === "user";
		if ((e || !n) && (n = {
			id: r.id,
			steps: 0,
			groups: []
		}, t.push(n), e)) {
			n.user = r, n.groups.push({
				notice: !1,
				activities: []
			});
			continue;
		}
		let i = r.type === "notice", a = n.groups.at(-1);
		(!a || a.notice !== i) && (a = {
			notice: i,
			activities: []
		}, n.groups.push(a)), a.activities.push(r), i || (n.steps++, n.last = r, r.type === "message" && r.role === "assistant" && (n.answer = r));
	}
	return t;
}
function Ds({ turn: e, followedByTurn: t, active: n, labels: r, toolActivityRenderer: i, expanded: a, onToggle: o }) {
	let { user: s, answer: c } = e, l = !n && s && c && e.steps > 1 && (c.replayCompleted ?? (c.timestamp !== void 0 || t && s.timestamp === void 0 && e.last === c)), u = l && s.timestamp !== void 0 && c.timestamp !== void 0 ? Math.max(0, Math.floor((c.timestamp - s.timestamp) / 1e3)) : void 0, d = (t) => /* @__PURE__ */ W(Os, {
		activity: t,
		labels: r,
		toolActivityRenderer: i,
		running: n && t === e.last,
		showMessageActions: !n && t === c
	}, t.id);
	return /* @__PURE__ */ W(F, { children: e.groups.map((t, n) => {
		if (t.notice) return /* @__PURE__ */ W("div", {
			className: "paui-notice-group",
			children: t.activities.map(d)
		}, n);
		let i = l && !a ? t.activities.includes(c) ? d(c) : null : t.activities.map(d);
		return n > 0 && !i ? null : /* @__PURE__ */ W("article", {
			className: "paui-turn",
			children: [n === 0 && s && /* @__PURE__ */ W(Rs, {
				message: s,
				labels: r,
				showActions: !0
			}), (t.activities.length > 0 || l) && /* @__PURE__ */ W("div", {
				className: "paui-activities",
				children: [n === 0 && l && /* @__PURE__ */ W("button", {
					type: "button",
					className: "paui-turn-summary",
					"aria-expanded": a,
					onClick: () => o(e.id),
					children: [
						r.turnCompleted(u),
						" ",
						/* @__PURE__ */ W("span", {
							"aria-hidden": "true",
							children: a ? "⌃" : "⌄"
						})
					]
				}), i]
			})]
		}, n);
	}) });
}
var Os = pt(function({ activity: e, labels: t, toolActivityRenderer: n, running: r, showMessageActions: i }) {
	return /* @__PURE__ */ W("div", {
		className: "paui-activity",
		"data-pretty-aui-slot": "activity",
		"data-kind": e.type === "message" ? e.role : e.type === "tool" && e.subagent ? "subagent" : e.type,
		"data-level": e.type === "notice" ? e.level : void 0,
		"data-status": bc(e),
		children: /* @__PURE__ */ W(ks, {
			activity: e,
			labels: t,
			toolActivityRenderer: n,
			running: r,
			showMessageActions: i
		})
	});
});
function ks({ activity: e, labels: t, toolActivityRenderer: n, running: r, showMessageActions: i }) {
	switch (e.type) {
		case "message": return /* @__PURE__ */ W(Rs, {
			message: e,
			labels: t,
			running: r,
			showActions: i
		});
		case "context": return /* @__PURE__ */ W(As, {
			activity: e,
			labels: t
		});
		case "notice": return /* @__PURE__ */ W("div", {
			className: "paui-host-notice",
			role: e.level === "error" ? "alert" : "status",
			children: [/* @__PURE__ */ W("span", {
				className: "paui-host-notice__icon",
				"aria-hidden": "true",
				children: e.level === "error" ? /* @__PURE__ */ W(Qc, {}) : /* @__PURE__ */ W(Zc, {})
			}), /* @__PURE__ */ W("span", { children: e.text })]
		});
		case "tool": return e.subagent ? /* @__PURE__ */ W(Ps, {
			tool: e,
			labels: t,
			renderer: n
		}) : /* @__PURE__ */ W("details", {
			className: "paui-disclosure paui-tool",
			"data-state": e.status,
			children: [/* @__PURE__ */ W("summary", {
				className: "paui-flow-summary",
				children: [
					/* @__PURE__ */ W(Bs, { icon: /* @__PURE__ */ W(Ws, { kind: e.kind }) }),
					/* @__PURE__ */ W("span", {
						className: "paui-flow-title",
						children: Us(e.kind, t.tool)
					}),
					/* @__PURE__ */ W("span", {
						className: "paui-flow-separator",
						"aria-hidden": "true"
					}),
					/* @__PURE__ */ W("span", {
						className: "paui-flow-preview",
						children: e.title
					}),
					/* @__PURE__ */ W("span", {
						className: "paui-sr-only",
						children: e.status
					})
				]
			}), /* @__PURE__ */ W("div", {
				className: "paui-disclosure__body",
				children: /* @__PURE__ */ W(Gs, {
					tool: e,
					labels: t,
					renderer: n
				})
			})]
		});
		case "plan": return /* @__PURE__ */ W("details", {
			className: "paui-disclosure paui-plan",
			open: !0,
			children: [/* @__PURE__ */ W("summary", { children: [
				/* @__PURE__ */ W(Vc, {}),
				/* @__PURE__ */ W("span", { children: t.plan }),
				/* @__PURE__ */ W(Cc, { status: yc(e.entries) })
			] }), /* @__PURE__ */ W("ol", {
				className: "paui-plan__list",
				children: e.entries.map((e, t) => /* @__PURE__ */ W("li", {
					"data-status": e.status,
					children: [/* @__PURE__ */ W("span", {
						className: "paui-plan__mark",
						"aria-hidden": "true"
					}), /* @__PURE__ */ W("span", { children: e.content })]
				}, `${e.content}-${t}`))
			})]
		});
		case "terminal": return /* @__PURE__ */ W("details", {
			className: "paui-disclosure paui-terminal",
			children: [/* @__PURE__ */ W("summary", { children: [
				/* @__PURE__ */ W(Gc, {}),
				/* @__PURE__ */ W("span", { children: e.title }),
				/* @__PURE__ */ W(Cc, { status: e.exited ? "completed" : "in_progress" })
			] }), /* @__PURE__ */ W("pre", { children: e.output })]
		});
		case "unsupported": return /* @__PURE__ */ W("div", {
			className: "paui-unsupported",
			children: t.unsupportedContent(e.kind)
		});
	}
}
function As({ activity: e, labels: t }) {
	return /* @__PURE__ */ W("details", {
		className: "paui-disclosure paui-context-injection",
		children: [/* @__PURE__ */ W("summary", {
			className: "paui-flow-summary",
			children: [
				/* @__PURE__ */ W(Bs, { icon: /* @__PURE__ */ W(Xc, {}) }),
				/* @__PURE__ */ W("span", {
					className: "paui-flow-title",
					children: t.contextInjection
				}),
				/* @__PURE__ */ W("span", {
					className: "paui-flow-separator",
					"aria-hidden": "true"
				}),
				/* @__PURE__ */ W("span", {
					className: "paui-flow-preview",
					children: e.label
				})
			]
		}), /* @__PURE__ */ W("div", {
			className: "paui-context-injection__body",
			tabIndex: 0,
			children: e.content.map((n, r) => /* @__PURE__ */ W(js, {
				block: n,
				labels: t
			}, `${e.id}:${r}`))
		})]
	});
}
function js({ block: e, labels: t }) {
	if (e.type === "text" && typeof e.text == "string") return /* @__PURE__ */ W(Ms, {
		text: e.text,
		labels: t
	});
	if (e.type === "resource" && Sc(e.resource)) {
		let n = e.resource;
		return /* @__PURE__ */ W("section", {
			className: "paui-context-block",
			children: [/* @__PURE__ */ W("div", {
				className: "paui-context-meta",
				children: [/* @__PURE__ */ W("span", { children: String(n.uri ?? t.resource) }), typeof n.mimeType == "string" ? /* @__PURE__ */ W("span", { children: n.mimeType }) : null]
			}), typeof n.text == "string" ? /* @__PURE__ */ W(Ms, {
				text: n.text,
				labels: t
			}) : typeof n.blob == "string" ? /* @__PURE__ */ W("span", {
				className: "paui-muted",
				children: `Binary resource · ${n.blob.length.toLocaleString()} base64 characters`
			}) : null]
		});
	}
	if (e.type === "resource_link" && typeof e.uri == "string") {
		let n = typeof e.title == "string" ? e.title : typeof e.name == "string" ? e.name : t.resource, r = typeof e.mimeType == "string" ? e.mimeType : void 0, i = typeof e.description == "string" ? e.description : void 0;
		return /* @__PURE__ */ W("section", {
			className: "paui-context-block",
			children: [
				/* @__PURE__ */ W("div", {
					className: "paui-context-meta",
					children: [/* @__PURE__ */ W("span", { children: n }), r ? /* @__PURE__ */ W("span", { children: r }) : null]
				}),
				/* @__PURE__ */ W("span", {
					className: "paui-context-identifier",
					children: e.uri
				}),
				i ? /* @__PURE__ */ W("span", { children: i }) : null
			]
		});
	}
	return (e.type === "image" || e.type === "audio") && typeof e.mimeType == "string" && typeof e.data == "string" ? /* @__PURE__ */ W("span", {
		className: "paui-context-meta",
		children: `${Us(e.type, e.type)} · ${e.mimeType} · ${e.data.length.toLocaleString()} base64 characters`
	}) : /* @__PURE__ */ W(Ms, {
		text: Ao(e),
		labels: t
	});
}
function Ms({ text: e, labels: t }) {
	let n = Ns(e);
	return /* @__PURE__ */ W(F, { children: [/* @__PURE__ */ W("pre", {
		className: "paui-context-text",
		children: n.text
	}), n.truncated ? /* @__PURE__ */ W("span", {
		className: "paui-context-truncated",
		children: t.contextTruncated(e.length)
	}) : null] });
}
function Ns(e) {
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
function Ps({ tool: e, labels: t, renderer: n }) {
	let { controller: r, snapshot: i, runAction: a } = hs("ChatTranscript"), o = e.subagent, s = e.status === "pending" || e.status === "in_progress", c = Fs(e.id, s), l = Ls(e, t), u = i.capabilities.loadSession || i.capabilities.resumeSession;
	return /* @__PURE__ */ W("div", {
		className: "paui-subagent-row",
		children: [/* @__PURE__ */ W("details", {
			className: "paui-disclosure paui-subagent",
			"data-state": e.status,
			"data-running": s || void 0,
			children: [/* @__PURE__ */ W("summary", {
				className: "paui-flow-summary",
				children: [
					/* @__PURE__ */ W(Bs, { icon: /* @__PURE__ */ W(zc, {}) }),
					/* @__PURE__ */ W("span", {
						className: "paui-flow-title",
						children: t.agentName(o.agent)
					}),
					o.description ? /* @__PURE__ */ W(F, { children: [/* @__PURE__ */ W("span", {
						className: "paui-flow-separator",
						"aria-hidden": "true"
					}), /* @__PURE__ */ W("span", {
						className: "paui-flow-preview",
						children: o.description
					})] }) : null,
					/* @__PURE__ */ W("span", {
						className: "paui-subagent-status",
						"data-status": e.status,
						children: [s ? /* @__PURE__ */ W("span", {
							className: "paui-subagent-status__ongoing",
							children: [/* @__PURE__ */ W("span", {
								className: "paui-subagent-status__spinner",
								"aria-hidden": "true"
							}), /* @__PURE__ */ W("span", { children: t.agentOngoing })]
						}) : /* @__PURE__ */ W("span", { children: l }), c ? /* @__PURE__ */ W("span", { children: t.agentObserved(c) }) : null]
					})
				]
			}), /* @__PURE__ */ W("div", {
				className: "paui-disclosure__body",
				children: /* @__PURE__ */ W(Gs, {
					tool: e,
					labels: t,
					renderer: n
				})
			})]
		}), o.sessionId ? /* @__PURE__ */ W("button", {
			className: "paui-subagent-open",
			type: "button",
			disabled: !u || i.phase !== "idle",
			"aria-label": t.openChildSession,
			onClick: () => a(() => r.openChildSession(o.sessionId)),
			children: /* @__PURE__ */ W(Bc, {})
		}) : null]
	});
}
function Fs(e, t) {
	let n = V(Date.now()), [r, i] = z(n.current);
	return B(() => {
		n.current = Date.now(), i(n.current);
	}, [e]), B(() => {
		if (!t) return;
		let e = window.setInterval(() => i(Date.now()), 1e3);
		return () => window.clearInterval(e);
	}, [t]), t ? Is(r - n.current) : void 0;
}
function Is(e) {
	let t = Math.max(0, Math.floor(e / 1e3));
	if (t < 60) return `${t}s`;
	let n = Math.floor(t / 60), r = t % 60;
	return n < 60 ? `${n}m ${String(r).padStart(2, "0")}s` : `${Math.floor(n / 60)}h ${String(n % 60).padStart(2, "0")}m`;
}
function Ls(e, t) {
	return e.subagent?.background && e.status === "completed" ? t.agentBackground : e.status === "completed" ? t.agentCompleted : e.status === "failed" ? t.agentFailed : e.status === "cancelled" ? t.agentCancelled : Us(e.status, t.agentCompleted);
}
function Rs({ message: e, labels: t, running: n = !1, showActions: r = !1 }) {
	return e.role === "thought" ? /* @__PURE__ */ W(zs, {
		message: e,
		labels: t,
		running: n
	}) : /* @__PURE__ */ W("div", {
		className: "paui-message",
		"data-pretty-aui-slot": "message",
		"data-role": e.role,
		"data-pending": e.pending || void 0,
		"aria-live": e.role === "assistant" && n ? "polite" : void 0,
		"aria-atomic": e.role === "assistant" && n ? "false" : void 0,
		children: [/* @__PURE__ */ W("div", {
			className: "paui-message__bubble",
			children: [/* @__PURE__ */ W("span", {
				className: "paui-message__label",
				children: e.role === "user" ? t.you : t.assistantName
			}), /* @__PURE__ */ W("div", {
				className: "paui-message__content",
				children: e.content.map((e, n) => /* @__PURE__ */ W(Ys, {
					block: e,
					labels: t
				}, n))
			})]
		}), r ? /* @__PURE__ */ W(po, {
			content: e.content,
			timestamp: e.timestamp,
			clock: e.role === "user" ? "start" : "end",
			labels: t
		}) : null]
	});
}
function zs({ message: e, labels: t, running: n }) {
	let r = V(null), i = Vs(e.content, n);
	return Ze(() => {
		let e = r.current;
		e && (e.scrollLeft = n ? e.scrollWidth - e.clientWidth : 0);
	}, [i, n]), /* @__PURE__ */ W("details", {
		className: "paui-thought",
		"data-running": n || void 0,
		children: [/* @__PURE__ */ W("summary", {
			className: "paui-flow-summary",
			children: [
				/* @__PURE__ */ W(Bs, { icon: /* @__PURE__ */ W(Hc, {}) }),
				/* @__PURE__ */ W("span", {
					className: "paui-flow-title",
					children: t.thinking
				}),
				i ? /* @__PURE__ */ W(F, { children: [/* @__PURE__ */ W("span", {
					className: "paui-flow-separator",
					"aria-hidden": "true"
				}), /* @__PURE__ */ W("span", {
					ref: r,
					className: "paui-flow-preview",
					"data-follow-end": n || void 0,
					children: i
				})] }) : null
			]
		}), /* @__PURE__ */ W("div", {
			className: "paui-thought__body",
			children: e.content.map((e, n) => /* @__PURE__ */ W(Ys, {
				block: e,
				labels: t
			}, n))
		})]
	});
}
function Bs({ icon: e }) {
	return /* @__PURE__ */ W("span", {
		className: "paui-flow-leading",
		"aria-hidden": "true",
		children: [/* @__PURE__ */ W("span", {
			className: "paui-flow-icon",
			children: e
		}), /* @__PURE__ */ W("span", {
			className: "paui-flow-chevron",
			children: /* @__PURE__ */ W(Ic, {})
		})]
	});
}
function Vs(e, t) {
	if (t) {
		for (let t = e.length - 1; t >= 0; --t) {
			let n = Hs(e[t]).trimEnd();
			if (n) return n.slice(n.lastIndexOf("\n") + 1).replace(/\r$/, "").trim();
		}
		return "";
	}
	let n = e.map(Hs).filter(Boolean).join("\n").trimEnd();
	return n ? n.split(/\r?\n/)[0]?.trim() ?? "" : "";
}
function Hs(e) {
	return e.type === "text" && typeof e.text == "string" ? e.text : e.type === "resource" && Sc(e.resource) && typeof e.resource.text == "string" ? e.resource.text : "";
}
function Us(e, t) {
	if (!e) return t;
	let n = e.replaceAll(/[_-]+/g, " ").trim();
	return n ? `${n[0].toUpperCase()}${n.slice(1)}` : t;
}
function Ws({ kind: e }) {
	let t = e?.toLowerCase() ?? "";
	return t.includes("read") || t.includes("browse") || t.includes("context") ? /* @__PURE__ */ W(Uc, {}) : t.includes("search") || t.includes("find") ? /* @__PURE__ */ W(Wc, {}) : t.includes("bash") || t.includes("shell") || t.includes("terminal") || t.includes("execute") ? /* @__PURE__ */ W(Gc, {}) : /* @__PURE__ */ W(Rc, {});
}
function Gs({ tool: e, labels: t, renderer: n }) {
	let r = /* @__PURE__ */ W(Ks, {
		tool: e,
		labels: t
	});
	return n ? /* @__PURE__ */ W(Js, {
		fallback: r,
		resetKey: e.id,
		children: /* @__PURE__ */ W(qs, {
			tool: e,
			renderer: n,
			fallback: r
		})
	}, e.id) : r;
}
function Ks({ tool: e, labels: t }) {
	return /* @__PURE__ */ W(Qo, {
		tool: e,
		labels: t,
		renderContent: (e, n) => /* @__PURE__ */ W(Xs, {
			value: e,
			labels: t
		}, n)
	});
}
function qs({ tool: e, renderer: t, fallback: n }) {
	let r = t(e);
	return r === void 0 ? n : r;
}
var Js = class extends I {
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
function Ys({ block: e, labels: t }) {
	let n = Qe(() => e.type === "text" && typeof e.text == "string" ? fc(e.text) : void 0, [e]);
	if (n !== void 0) return /* @__PURE__ */ W("div", {
		className: "paui-markdown",
		dangerouslySetInnerHTML: { __html: n }
	});
	if (e.type === "image_unavailable") return /* @__PURE__ */ W("span", {
		title: t.imageUnavailableDetails,
		children: t.imageUnavailable
	});
	if (e.type === "image" && typeof e.data == "string" && typeof e.mimeType == "string" && e.mimeType.startsWith("image/")) return /* @__PURE__ */ W("img", {
		className: "paui-media",
		src: `data:${e.mimeType};base64,${e.data}`,
		alt: ""
	});
	if (e.type === "audio" && typeof e.data == "string" && typeof e.mimeType == "string" && e.mimeType.startsWith("audio/")) return /* @__PURE__ */ W("audio", {
		className: "paui-media",
		controls: !0,
		src: `data:${e.mimeType};base64,${e.data}`
	});
	if (e.type === "resource_link" && typeof e.uri == "string") {
		let n = typeof e.title == "string" ? e.title : typeof e.name == "string" ? e.name : e.uri;
		return hc(e.uri) ? /* @__PURE__ */ W("a", {
			className: "paui-resource",
			href: e.uri,
			target: "_blank",
			rel: "noreferrer",
			children: [/* @__PURE__ */ W(qc, {}), /* @__PURE__ */ W("span", { children: n })]
		}) : /* @__PURE__ */ W("span", {
			className: "paui-unsupported",
			children: t.unsupportedContent(t.unsafeResourceLink)
		});
	}
	if (e.type === "resource" && Sc(e.resource)) {
		let n = e.resource, r = typeof n.uri == "string" ? n.uri : t.resource;
		return typeof n.text == "string" ? /* @__PURE__ */ W("details", {
			className: "paui-resource",
			children: [/* @__PURE__ */ W("summary", { children: [/* @__PURE__ */ W(Jc, {}), r] }), /* @__PURE__ */ W("pre", { children: n.text })]
		}) : /* @__PURE__ */ W("span", {
			className: "paui-resource",
			children: [/* @__PURE__ */ W(Jc, {}), r]
		});
	}
	return /* @__PURE__ */ W("span", {
		className: "paui-unsupported",
		children: t.unsupportedContent(e.type)
	});
}
function Xs({ value: e, labels: t }) {
	if (!Sc(e)) return null;
	if (e.type === "content" && Sc(e.content) && typeof e.content.type == "string") return /* @__PURE__ */ W(Ys, {
		block: e.content,
		labels: t
	});
	if (e.type === "diff") {
		let n = typeof e.path == "string" ? e.path : t.changedFiles, r = typeof e.patch == "string" ? e.patch : typeof e.newText == "string" ? e.newText : void 0;
		return /* @__PURE__ */ W("details", {
			className: "paui-diff",
			children: [/* @__PURE__ */ W("summary", { children: [/* @__PURE__ */ W(Yc, {}), n] }), r ? /* @__PURE__ */ W("pre", { children: r }) : /* @__PURE__ */ W("span", {
				className: "paui-muted",
				children: t.binaryChange
			})]
		});
	}
	return e.type === "terminal" ? /* @__PURE__ */ W("span", {
		className: "paui-muted",
		children: [
			/* @__PURE__ */ W(Gc, {}),
			" ",
			t.terminalOutputInActivity
		]
	}) : /* @__PURE__ */ W("span", {
		className: "paui-unsupported",
		children: t.unsupportedContent(typeof e.type == "string" ? e.type : t.toolResult)
	});
}
function Zs() {
	let { controller: e, snapshot: t, labels: n, runAction: r, ids: i } = hs("ChatComposer"), a = t.draft.text, [o, s] = z(0), [c, l] = z(!1), u = V(!1), d = V(null), f = V(null), p = _c(t), m = V(null), [h, g] = z(!1);
	B(() => {
		g(!0);
	}, []);
	let _ = V(0);
	Ze(() => (_.current++, () => {
		_.current++;
	}), [p]);
	let v = (i) => r(async () => {
		let r = t.sessionInstanceId, a = _.current;
		if (!t.promptCapabilities.image) throw Error(n.imagesUnsupported);
		let o = await Wn(i, e.getSnapshot().draft.images).catch((e) => {
			throw e instanceof Hn ? Error(n.imageError(e.issue)) : e;
		});
		r === e.getSnapshot().sessionInstanceId && _.current === a && e.addDraftImages(o);
	}), y = Qe(() => e.getComposerActions(), [e, t.composerActionsRevision]), b = (t) => r(async () => {
		await e.runComposerAction(t) && d.current?.focus();
	}), x = t.configOptions.find((e) => e.category === "mode" || e.id === "mode"), S = t.configOptions.find((e) => e.type === "select" && (e.category === "model" || e.id === "model")), C = t.configOptions.find((e) => e.type === "select" && (e.category === "thought_level" || e.id === "effort")), w = () => [
		{
			id: "images",
			label: n.addImages,
			disabled: !t.promptCapabilities.image,
			...t.promptCapabilities.image ? {} : { description: n.imagesUnsupported },
			run: () => {
				m.current?.click();
			}
		},
		...t.contextSelection.canAdd ? [{
			id: "context",
			label: n.addContext,
			disabled: t.contextSelection.busy,
			run: async () => {
				await e.addContext();
			}
		}] : [],
		...y.filter((e) => !e.placement),
		{
			id: "commands",
			label: n.commands,
			children: t.commands.map((t) => ({
				id: `command:${t.name}`,
				label: `/${t.name}`,
				description: t.description,
				run: () => {
					e.selectCommand(t.name), d.current?.focus();
				}
			}))
		}
	], T = t.activities.some((e) => e.type !== "notice") || t.interactions.length || t.phase === "auth_required" || t.error ? "docked" : "hero";
	Ze(() => {
		let e = d.current;
		e && (e.style.height = "0px", e.style.height = `${Math.min(e.scrollHeight, 336)}px`);
	}, [T, a]);
	let E = !t.sessionId || t.phase === "connecting" || t.phase === "auth_required" || t.phase === "closed", D = E || t.draft.locked, O = t.phase === "running" || t.phase === "awaiting_user" || t.phase === "cancelling", ee = () => {
		!a.trim() && !t.draft.images.length || D || O || (l(!0), r(async () => {
			await e.sendDraft().done;
		}));
	}, k = !t.draft.locked && a.startsWith("/") && !/\s/.test(a.slice(1)) && !c ? t.commands.filter((e) => e.name.startsWith(a.slice(1).split(/\s/, 1)[0] ?? "")) : [], te = Math.min(o, Math.max(0, k.length - 1)), ne = (t) => {
		e.setDraft(`/${t} `), l(!0), d.current?.focus();
	}, re = (e) => {
		if (!e.repeat) {
			if (k.length && e.key === "ArrowDown") {
				e.preventDefault(), s((te + 1) % k.length);
				return;
			}
			if (k.length && e.key === "ArrowUp") {
				e.preventDefault(), s((te - 1 + k.length) % k.length);
				return;
			}
			if (k.length && e.key === "Escape") {
				e.preventDefault(), l(!0);
				return;
			}
			if (k.length && e.key === "Tab" && !e.shiftKey) {
				e.preventDefault();
				let t = k[te];
				t && ne(t.name);
				return;
			}
			if (e.key === "Enter" && !e.shiftKey && !u.current && !e.nativeEvent.isComposing) {
				e.preventDefault();
				let t = k[te];
				t ? ne(t.name) : ee();
			}
		}
	}, A = `${i.instance}-commands`;
	return Ze(() => Qn(f.current), [k.length, T]), Ze(() => {
		let e = f.current, t = e?.querySelector(`#${A}-${te}`);
		!e || !t || (t.offsetTop < e.scrollTop ? e.scrollTop = t.offsetTop : t.offsetTop + t.offsetHeight > e.scrollTop + e.clientHeight && (e.scrollTop = t.offsetTop + t.offsetHeight - e.clientHeight));
	}, [
		A,
		k.length,
		te
	]), /* @__PURE__ */ W("footer", {
		className: "paui-composer-wrap",
		"data-pretty-aui-slot": "composer",
		"data-placement": T,
		children: [k.length ? /* @__PURE__ */ W("div", {
			ref: f,
			className: "paui-commands",
			role: "listbox",
			id: A,
			"aria-label": n.commands,
			children: k.map((e, t) => /* @__PURE__ */ W("button", {
				type: "button",
				id: `${A}-${t}`,
				role: "option",
				"aria-selected": t === te,
				onMouseDown: (e) => e.preventDefault(),
				onClick: () => ne(e.name),
				children: [/* @__PURE__ */ W("code", { children: ["/", e.name] }), /* @__PURE__ */ W("span", { children: e.description })]
			}, e.name))
		}) : null, /* @__PURE__ */ W("div", {
			className: "paui-composer-unit",
			children: [y.some((e) => e.placement === "shortcut") && /* @__PURE__ */ W("div", {
				className: "paui-shortcuts",
				children: y.filter((e) => e.placement === "shortcut").map((e) => e.children ? /* @__PURE__ */ W(Xn, {
					label: e.label,
					variant: "shortcut",
					actions: e.children,
					disabled: D || !!e.disabled,
					onOpen: () => l(!0),
					onChoose: b
				}, p + e.id) : /* @__PURE__ */ W("button", {
					className: "paui-shortcut",
					type: "button",
					disabled: D || e.disabled,
					onClick: () => b(e),
					children: e.label
				}, e.id))
			}), /* @__PURE__ */ W("div", {
				className: "paui-composer",
				"data-pretty-aui-slot": "composer-input",
				onDragOver: (e) => {
					e.dataTransfer.types.includes("Files") && e.preventDefault();
				},
				onDrop: (e) => {
					e.dataTransfer.files.length && (e.preventDefault(), e.stopPropagation(), D || v(Array.from(e.dataTransfer.files)));
				},
				children: [
					h && /* @__PURE__ */ W("input", {
						ref: m,
						type: "file",
						accept: "image/png,image/jpeg,image/webp,image/gif",
						multiple: !0,
						hidden: !0,
						onChange: (e) => {
							let t = Array.from(e.currentTarget.files ?? []);
							e.currentTarget.value = "", t.length && v(t);
						}
					}),
					t.draft.images.length > 0 && /* @__PURE__ */ W("div", {
						className: "paui-composer-images",
						role: "group",
						"aria-label": n.addImages,
						children: [/* @__PURE__ */ W(Yn, {
							images: t.draft.images,
							sessionInstanceId: t.sessionInstanceId,
							disabled: D,
							remove: (t) => e.removeDraftImage(t),
							labels: n
						}), /* @__PURE__ */ W("small", { children: n.imageBudget(Ht(t.draft.images), 8388608 - Ht(t.draft.images)) })]
					}),
					t.draft.recoverable.map((t, i) => {
						let a = (t.text || t.images.map((e) => e.name).join(", ")).replace(/\s+/g, " ").slice(0, 80);
						return /* @__PURE__ */ W("button", {
							type: "button",
							disabled: D,
							"aria-label": `${n.recoverDraft} ${i + 1}: ${a}`,
							onClick: () => r(async () => e.recoverDraft(t.id)),
							children: [
								n.recoverDraft,
								" ",
								/* @__PURE__ */ W("small", { children: [
									i + 1,
									". ",
									a
								] })
							]
						}, t.id);
					}),
					t.contextSelection.items.length ? /* @__PURE__ */ W("div", {
						className: "paui-composer__context",
						"data-pretty-aui-slot": "composer-context",
						role: "group",
						"aria-label": n.contextSelection,
						children: t.contextSelection.items.map((i) => /* @__PURE__ */ W("span", {
							className: "paui-context-chip",
							"data-pretty-aui-slot": "composer-context-item",
							title: i.label,
							children: [/* @__PURE__ */ W("span", {
								className: "paui-context-chip__label",
								children: i.label
							}), t.contextSelection.canRemove ? /* @__PURE__ */ W("button", {
								type: "button",
								"aria-label": n.removeContext(i.label),
								title: n.removeContext(i.label),
								disabled: D || O || t.contextSelection.busy,
								onMouseDown: (e) => e.preventDefault(),
								onClick: () => r(() => e.removeContext(i.id)),
								children: /* @__PURE__ */ W("span", {
									"aria-hidden": "true",
									children: "×"
								})
							}) : null]
						}, i.id))
					}) : null,
					/* @__PURE__ */ W("textarea", {
						ref: d,
						rows: 1,
						value: a,
						disabled: E,
						readOnly: t.draft.locked,
						"aria-busy": t.draft.locked || void 0,
						onPaste: (e) => {
							if (e.clipboardData.getData("text/plain")) return;
							let t = Array.from(e.clipboardData.files);
							t.length && (e.preventDefault(), D || v(t));
						},
						placeholder: n.composerPlaceholder,
						"aria-label": n.composerPlaceholder,
						role: "combobox",
						"aria-autocomplete": "list",
						"aria-haspopup": "listbox",
						"aria-controls": k.length ? A : void 0,
						"aria-expanded": !!k.length,
						"aria-activedescendant": k.length ? `${A}-${te}` : void 0,
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
						onKeyDown: re
					}),
					/* @__PURE__ */ W("div", {
						className: "paui-composer__actions",
						"data-pretty-aui-slot": "composer-actions",
						children: [
							/* @__PURE__ */ W(Xn, {
								label: n.composerAdd,
								variant: "add",
								actions: w,
								disabled: D,
								onOpen: () => l(!0),
								onChoose: b
							}, p),
							x && /* @__PURE__ */ W(Qs, {
								controller: e,
								options: [x]
							}),
							/* @__PURE__ */ W(Qs, {
								controller: e,
								options: t.configOptions.filter((e) => e !== x && e !== S && e !== C)
							}),
							/* @__PURE__ */ W("span", { className: "paui-composer-spacer" }),
							S ? /* @__PURE__ */ W(zn, {
								model: S,
								effort: C,
								labels: n,
								onSelect: (t, n) => e.setConfigOption(t, n),
								runAction: r
							}, p + S.id) : C && /* @__PURE__ */ W($s, {
								controller: e,
								label: C.name,
								option: C
							}, p + C.id),
							O ? /* @__PURE__ */ W("button", {
								className: "paui-send paui-stop",
								type: "button",
								onMouseDown: (e) => e.preventDefault(),
								onClick: () => r(() => e.cancel()),
								disabled: t.phase === "cancelling",
								children: [/* @__PURE__ */ W(Nc, {}), /* @__PURE__ */ W("span", {
									className: "paui-sr-only",
									children: n.stop
								})]
							}) : /* @__PURE__ */ W("button", {
								className: "paui-send",
								type: "button",
								onMouseDown: (e) => e.preventDefault(),
								onClick: ee,
								disabled: D || !a.trim() && !t.draft.images.length,
								children: [/* @__PURE__ */ W(Mc, {}), /* @__PURE__ */ W("span", {
									className: "paui-sr-only",
									children: n.send
								})]
							})
						]
					})
				]
			})]
		})]
	});
}
function Qs({ controller: e, options: t }) {
	let { labels: n, runAction: r } = hs("ChatComposer");
	return /* @__PURE__ */ W("div", {
		className: "paui-config",
		children: t.map((t) => {
			let i = ec(t, n);
			return t.type === "boolean" ? /* @__PURE__ */ W("label", {
				title: t.description,
				children: [/* @__PURE__ */ W("input", {
					type: "checkbox",
					checked: !!t.currentValue,
					onChange: (n) => r(() => e.setConfigOption(t.id, n.target.checked))
				}), /* @__PURE__ */ W("span", { children: i })]
			}, t.id) : t.type === "select" ? /* @__PURE__ */ W($s, {
				controller: e,
				label: i,
				option: t
			}, t.id) : null;
		})
	});
}
function $s({ controller: e, label: t, option: n }) {
	let { runAction: r } = hs("ChatComposer"), i = V(null), a = V(null), o = V(null), s = `paui-config-${H().replaceAll(":", "")}`, c = n.options ?? [], l = c.findIndex((e) => e.value === String(n.currentValue)), u = l >= 0 ? c[l] : void 0, [d, f] = z(!1), [p, m] = z(Math.max(0, l)), h = (e = Math.max(0, l)) => {
		c.length && (m(e), f(!0));
	}, g = (e = !1) => {
		f(!1), e && a.current?.focus();
	}, _ = (t) => {
		let i = c[t];
		i && (g(!0), i.value !== String(n.currentValue) && r(() => e.setConfigOption(n.id, i.value)));
	}, v = (e) => {
		c.length && m((t) => (t + e + c.length) % c.length);
	};
	return B(() => {
		if (!d) return;
		let e = (e) => {
			i.current && e.composedPath().includes(i.current) || f(!1);
		};
		return window.addEventListener("pointerdown", e, !0), () => window.removeEventListener("pointerdown", e, !0);
	}, [d]), B(() => {
		d && (o.current?.querySelector(`#${s}-option-${p}`))?.scrollIntoView?.({ block: "nearest" });
	}, [
		p,
		s,
		d
	]), /* @__PURE__ */ W("div", {
		className: "paui-config__field",
		ref: i,
		children: [/* @__PURE__ */ W("button", {
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
			children: [/* @__PURE__ */ W("span", { children: u?.name ?? String(n.currentValue) }), /* @__PURE__ */ W(Ic, {})]
		}), d ? /* @__PURE__ */ W("div", {
			ref: o,
			className: "paui-config__listbox",
			id: s,
			role: "listbox",
			"aria-label": t,
			children: c.map((e, t) => /* @__PURE__ */ W("button", {
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
				children: [/* @__PURE__ */ W("span", { children: e.name }), /* @__PURE__ */ W("span", {
					className: "paui-config__check",
					"aria-hidden": "true",
					children: e.value === String(n.currentValue) ? /* @__PURE__ */ W(Lc, {}) : null
				})]
			}, e.value))
		}) : null]
	});
}
function ec(e, t) {
	return e.category === "mode" || e.id === "mode" ? t.mode : e.name;
}
function tc({ interaction: e, controller: t, labels: n }) {
	let { ids: r } = hs("ChatInteractions"), i = `${r.instance}-${e.id}-title`;
	return /* @__PURE__ */ W("section", {
		className: "paui-interaction",
		role: "alertdialog",
		"aria-labelledby": i,
		children: [/* @__PURE__ */ W("div", {
			className: "paui-interaction__icon",
			children: /* @__PURE__ */ W(Kc, {})
		}), /* @__PURE__ */ W("div", {
			className: "paui-interaction__content",
			children: [
				/* @__PURE__ */ W("strong", {
					id: i,
					children: e.title || n.permission
				}),
				e.description ? /* @__PURE__ */ W("p", { children: e.description }) : null,
				/* @__PURE__ */ W("div", {
					className: "paui-interaction__actions",
					children: [e.options.map((n, r) => /* @__PURE__ */ W("button", {
						type: "button",
						className: n.kind.startsWith("reject") ? "paui-button-secondary" : r === 0 ? "paui-button-primary" : "paui-button-secondary",
						onClick: () => t.respondPermission(e.id, {
							outcome: "selected",
							optionId: n.id
						}),
						children: n.name
					}, n.id)), /* @__PURE__ */ W("button", {
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
function nc({ interaction: e, controller: t, labels: n }) {
	let { ids: r } = hs("ChatInteractions"), i = `${r.instance}-${e.id}-title`;
	if (e.mode === "url" && e.url) {
		let r = hc(e.url);
		return /* @__PURE__ */ W("section", {
			className: "paui-interaction",
			role: "dialog",
			"aria-labelledby": i,
			children: [/* @__PURE__ */ W("div", {
				className: "paui-interaction__icon",
				children: /* @__PURE__ */ W(qc, {})
			}), /* @__PURE__ */ W("div", {
				className: "paui-interaction__content",
				children: [
					/* @__PURE__ */ W("strong", {
						id: i,
						children: e.message
					}),
					/* @__PURE__ */ W("code", {
						className: "paui-url",
						children: e.url
					}),
					/* @__PURE__ */ W("div", {
						className: "paui-interaction__actions",
						children: [
							/* @__PURE__ */ W("button", {
								className: "paui-button-primary",
								type: "button",
								disabled: !r,
								onClick: () => r ? window.open(e.url, "_blank", "noopener,noreferrer") : void 0,
								children: n.openLink
							}),
							/* @__PURE__ */ W("button", {
								className: "paui-button-secondary",
								type: "button",
								onClick: () => t.respondElicitation(e.id, { action: "accept" }),
								children: n.finish
							}),
							/* @__PURE__ */ W("button", {
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
	return /* @__PURE__ */ W(rc, {
		interaction: e,
		controller: t,
		labels: n,
		titleId: i
	});
}
function rc({ interaction: e, controller: t, labels: n, titleId: r }) {
	let i = e.requestedSchema, a = Sc(i?.properties) ? i.properties : {}, o = Array.isArray(i?.required) ? i.required.filter((e) => typeof e == "string") : [];
	return /* @__PURE__ */ W("form", {
		className: "paui-interaction paui-form",
		onSubmit: (n) => {
			n.preventDefault();
			let r = n.currentTarget, i = new FormData(r), o = {};
			for (let [e, t] of Object.entries(a)) if (Sc(t)) {
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
		children: [/* @__PURE__ */ W("div", {
			className: "paui-interaction__icon",
			children: /* @__PURE__ */ W(el, {})
		}), /* @__PURE__ */ W("div", {
			className: "paui-interaction__content",
			children: [
				/* @__PURE__ */ W("strong", {
					id: r,
					children: e.message
				}),
				/* @__PURE__ */ W("div", {
					className: "paui-fields",
					children: Object.entries(a).map(([e, t]) => Sc(t) ? /* @__PURE__ */ W(ic, {
						name: e,
						schema: t,
						required: o.includes(e)
					}, e) : null)
				}),
				/* @__PURE__ */ W("div", {
					className: "paui-interaction__actions",
					children: [/* @__PURE__ */ W("button", {
						className: "paui-button-primary",
						type: "submit",
						children: n.accept
					}), /* @__PURE__ */ W("button", {
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
function ic({ name: e, schema: t, required: n }) {
	let r = typeof t.title == "string" ? t.title : e, i = typeof t.description == "string" ? t.description : void 0, a = Array.isArray(t.enum) ? t.enum.filter((e) => typeof e == "string") : [];
	return t.type === "boolean" ? /* @__PURE__ */ W("label", {
		className: "paui-field paui-field--check",
		children: [/* @__PURE__ */ W("input", {
			name: e,
			type: "checkbox"
		}), /* @__PURE__ */ W("span", { children: r })]
	}) : a.length ? /* @__PURE__ */ W("label", {
		className: "paui-field",
		children: [
			/* @__PURE__ */ W("span", { children: r }),
			/* @__PURE__ */ W("select", {
				name: e,
				required: n,
				children: a.map((e) => /* @__PURE__ */ W("option", { children: e }, e))
			}),
			i ? /* @__PURE__ */ W("small", { children: i }) : null
		]
	}) : /* @__PURE__ */ W("label", {
		className: "paui-field",
		children: [
			/* @__PURE__ */ W("span", { children: r }),
			/* @__PURE__ */ W("input", {
				name: e,
				required: n,
				type: t.type === "number" || t.type === "integer" ? "number" : "text"
			}),
			i ? /* @__PURE__ */ W("small", { children: i }) : null
		]
	});
}
function ac() {
	let { controller: e, snapshot: t, labels: n, runAction: r } = hs("ChatInteractions");
	return /* @__PURE__ */ W("section", {
		className: "paui-auth",
		children: [
			/* @__PURE__ */ W(Kc, {}),
			/* @__PURE__ */ W("strong", { children: n.authRequired }),
			/* @__PURE__ */ W("div", { children: t.authMethods.map((t) => /* @__PURE__ */ W("button", {
				type: "button",
				onClick: () => r(() => e.authenticate(t.id)),
				children: t.name
			}, t.id)) })
		]
	});
}
function oc({ controller: e, snapshot: t, labels: n, decorations: r, organizationError: i, updateDecoration: a, onClose: o }) {
	let { ids: s } = hs("ChatHeader"), c = V(null), l = V(null), u = V(null), d = V(null), f = V(null), [p, m] = z(!1), [h, g] = z(), [_, v] = z(), [y, b] = z(), x = (e, t) => {
		f.current = e, v(t);
	}, [S, C] = z(!1), [w, T] = z(), [E, D] = z(""), O = V(void 0), ee = V(null);
	Ze(() => {
		if (!O.current || p || w) return;
		O.current = void 0;
		let e = l.current;
		e?.contains(cc(e)) || (ee.current ?? c.current)?.focus();
	}, [p, w]);
	let k = Qe(() => sc(t, r, S), [
		t.sessions,
		t.loadedSessions,
		r,
		S
	]), te = Qe(() => {
		let e = /* @__PURE__ */ new Map();
		for (let t of k) {
			let n = t.pinned ? "pinned" : "cwd:" + (t.cwd ?? ""), r = e.get(n);
			r ? r.push(t) : e.set(n, [t]);
		}
		return [...e];
	}, [k]), [ne, re] = z(() => /* @__PURE__ */ new Set()), [A, ie] = z(), j = A && k.find((e) => e.sessionId === A.id), ae = (e, t) => {
		let n = e.getBoundingClientRect(), r = l.current.getBoundingClientRect(), i = n.top - r.top < r.height / 2;
		ie({
			id: t,
			below: i,
			y: i ? n.top - r.top : r.bottom - n.bottom
		});
	}, M = k.find((e) => e.sessionId === _), N = Date.now(), oe = p || M?.loaded?.phase === "running" || M?.loaded?.phase === "cancelling" || (M?.loaded?.interactionCount ?? 0) > 0, se = $e((e = !1) => {
		let t = f.current;
		v(void 0), b(void 0), e && t?.isConnected && t.focus();
	}, []);
	B(() => {
		let e = cc(l.current), t = e instanceof HTMLElement ? e : void 0;
		return c.current?.focus(), () => {
			t?.isConnected && t.focus();
		};
	}, []), B(() => {
		t.capabilities.listSessions && !t.sessions && (m(!0), e.listSessions().catch((e) => g(e instanceof Error ? e.message : String(e))).finally(() => m(!1)));
	}, [
		e,
		t.capabilities.listSessions,
		t.sessions
	]), Ze(() => {
		if (!_) return;
		let e = l.current, t = u.current, n = f.current;
		if (!e || !t || !n) return;
		let r = e.getBoundingClientRect(), i = t.getBoundingClientRect(), a = n.getBoundingClientRect(), o = Math.max(8, r.width - i.width - 8), s = Math.min(Math.max(a.right - r.left - i.width, 8), o), c = a.bottom - r.top + 4, d = a.top - r.top - i.height - 4, p = c + i.height <= r.height - 8 ? c : d, m = Math.max(8, r.height - i.height - 8);
		b({
			left: s,
			top: Math.min(Math.max(p, 8), m)
		});
	}, [_]), Ze(() => {
		_ && y && d.current?.focus();
	}, [y, _]), B(() => {
		if (!_) return;
		let e = (e) => {
			let t = e.composedPath();
			u.current && t.includes(u.current) || f.current && t.includes(f.current) || se();
		}, t = () => se();
		return window.addEventListener("pointerdown", e, !0), window.addEventListener("scroll", t, !0), window.addEventListener("resize", t), () => {
			window.removeEventListener("pointerdown", e, !0), window.removeEventListener("scroll", t, !0), window.removeEventListener("resize", t);
		};
	}, [se, _]), B(() => {
		let e = (e) => {
			if (e.key === "Escape") {
				if (e.preventDefault(), _) {
					e.stopPropagation(), se(!0);
					return;
				}
				if (w) {
					O.current = w, T(void 0);
					return;
				}
				o();
				return;
			}
			if (e.key !== "Tab") return;
			let t = l.current ? [...l.current.querySelectorAll(uc)].filter((e) => !e.hasAttribute("disabled")) : [], n = (e) => getComputedStyle(e).display !== "none", r = t.find(n), i = t.reverse().find(n);
			if (!r || !i) return;
			let a = cc(l.current);
			e.shiftKey && a === r ? (e.preventDefault(), i.focus()) : (!e.shiftKey && a === i || !a || !l.current?.contains(a)) && (e.preventDefault(), r.focus());
		};
		return window.addEventListener("keydown", e, !0), () => window.removeEventListener("keydown", e, !0);
	}, [
		se,
		_,
		o,
		w
	]);
	let ce = async (t) => {
		m(!0), g(void 0);
		try {
			await e.openSession(t), o();
		} catch (e) {
			g(e instanceof Error ? e.message : String(e));
		} finally {
			m(!1);
		}
	}, le = async (t) => {
		m(!0), g(void 0);
		try {
			await e.listSessions(t);
		} catch (e) {
			g(e instanceof Error ? e.message : String(e));
		} finally {
			m(!1);
		}
	}, ue = async (e, t) => {
		O.current = e.sessionId, se(), ie(void 0), m(!0), g(void 0);
		try {
			await a?.(e, t), T(void 0);
		} catch (e) {
			g(e instanceof Error ? e.message : String(e));
		} finally {
			m(!1);
		}
	}, de = async (t) => {
		let i = t.title ?? n.sessionUntitled;
		if (!window.confirm(n.confirmDeleteSession(i))) {
			se(!0);
			return;
		}
		O.current = t.sessionId, se(), m(!0), g(void 0);
		try {
			await e.deleteSession(t.sessionId), r.has(t.sessionId) && await a?.(t, {
				pinned: !1,
				archived: !1,
				alias: ""
			});
		} catch (e) {
			g(e instanceof Error ? e.message : String(e));
		} finally {
			m(!1);
		}
	};
	return /* @__PURE__ */ W("div", {
		className: "paui-drawer-backdrop",
		role: "presentation",
		onMouseDown: (e) => {
			e.target === e.currentTarget && o();
		},
		children: /* @__PURE__ */ W("aside", {
			ref: l,
			className: "paui-drawer",
			role: "dialog",
			"aria-modal": "true",
			"aria-labelledby": s.sessionsTitle,
			children: [
				/* @__PURE__ */ W("header", { children: [
					/* @__PURE__ */ W("strong", {
						id: s.sessionsTitle,
						children: S ? n.archivedSessions : n.sessions
					}),
					a && /* @__PURE__ */ W("button", {
						className: "paui-session-switch",
						type: "button",
						onClick: () => {
							C(!S), T(void 0), se();
						},
						children: S ? n.sessions : n.archivedSessions
					}),
					/* @__PURE__ */ W("button", {
						ref: c,
						className: "paui-icon-button",
						type: "button",
						onClick: o,
						children: [/* @__PURE__ */ W(Ec, {}), /* @__PURE__ */ W("span", {
							className: "paui-sr-only",
							children: n.close
						})]
					})
				] }),
				/* @__PURE__ */ W("div", {
					className: "paui-session-list",
					onScroll: () => ie(void 0),
					children: [
						p && !t.sessions ? /* @__PURE__ */ W("span", {
							className: "paui-muted",
							children: "…"
						}) : null,
						!p && !k.length ? /* @__PURE__ */ W("span", {
							className: "paui-muted",
							children: n.noSessions
						}) : null,
						te.map(([e, r], i) => {
							let o = r[0]?.cwd, c = e === "pinned" ? n.pinned : o?.split(/[\\/]/).filter(Boolean).at(-1) || o || n.defaultWorkspace;
							return /* @__PURE__ */ W("div", {
								role: "group",
								"aria-label": c,
								children: [/* @__PURE__ */ W("button", {
									type: "button",
									className: "paui-session-group",
									title: e === "pinned" ? c : o,
									"aria-expanded": !ne.has(e),
									onClick: () => {
										re((t) => {
											let n = new Set(t);
											return n.has(e) ? n.delete(e) : n.add(e), n;
										}), se(), ie(void 0);
									},
									children: [W(e === "pinned" ? Oc : Ac, {}), /* @__PURE__ */ W("span", { children: c })]
								}), !ne.has(e) && r.map((e, r) => {
									let o = e.sessionId === t.sessionId, c = e.alias || (e.title ?? n.sessionUntitled), l = e.loaded?.interactionCount ? n.pendingInteractions(e.loaded.interactionCount) : e.loaded && e.loaded.phase !== "idle" ? n.sessionPhase(e.loaded.phase) : xc(e.updatedAt, N, n.sessionAge) || n.sessionTimeUnknown, u = !!a || t.capabilities.deleteSession && !o, d = e.sessionId === _, f = `${s.instance}-status-${i}-${r}`;
									return /* @__PURE__ */ W("div", {
										className: "paui-session",
										onContextMenu: (t) => {
											if (t.target instanceof Element && t.target.closest("form, .paui-session__actions")) return;
											let n = t.currentTarget.querySelector("[aria-haspopup=menu]:enabled");
											n && (t.preventDefault(), x(n, e.sessionId));
										},
										onPointerEnter: (t) => {
											t.pointerType === "mouse" && ae(t.currentTarget, e.sessionId);
										},
										onPointerLeave: () => ie(void 0),
										onFocusCapture: (t) => ae(t.currentTarget, e.sessionId),
										onBlurCapture: (e) => {
											e.currentTarget.contains(e.relatedTarget) || ie(void 0);
										},
										"data-active": o || void 0,
										"data-has-actions": u || void 0,
										"data-loaded": e.loaded !== void 0 || void 0,
										"data-menu-open": d || void 0,
										children: [w === e.sessionId ? /* @__PURE__ */ W("form", {
											className: "paui-session__rename",
											onSubmit: (t) => {
												t.preventDefault(), ue(e, { alias: E.trim() });
											},
											children: [
												/* @__PURE__ */ W("input", {
													autoFocus: !0,
													"aria-label": n.renameSession,
													maxLength: 256,
													value: E,
													onChange: (e) => D(e.target.value)
												}),
												/* @__PURE__ */ W("button", {
													type: "submit",
													disabled: p,
													children: n.accept
												}),
												/* @__PURE__ */ W("button", {
													type: "button",
													onClick: () => {
														O.current = e.sessionId, T(void 0);
													},
													children: n.cancel
												})
											]
										}) : /* @__PURE__ */ W("button", {
											className: "paui-session__select",
											type: "button",
											"aria-current": o ? "page" : void 0,
											"aria-describedby": e.fullTime ? `${f} ${f}-time` : f,
											disabled: p || o,
											onClick: () => void ce(e.sessionId),
											children: [
												e.loaded?.phase === "running" ? /* @__PURE__ */ W("span", {
													className: "paui-session__spinner",
													"aria-hidden": "true"
												}) : null,
												e.pinned && /* @__PURE__ */ W("span", {
													role: "img",
													"aria-label": n.pinned,
													title: n.pinned,
													children: /* @__PURE__ */ W(Oc, {})
												}),
												/* @__PURE__ */ W("strong", {
													className: "paui-session__title",
													children: /* @__PURE__ */ W("span", { children: c })
												})
											]
										}), /* @__PURE__ */ W("span", {
											className: "paui-session__trailing",
											children: [
												/* @__PURE__ */ W("span", {
													className: "paui-session__meta",
													id: f,
													children: l
												}),
												e.fullTime && /* @__PURE__ */ W("span", {
													hidden: !0,
													id: `${f}-time`,
													children: e.fullTime
												}),
												u && !w ? /* @__PURE__ */ W("span", {
													className: "paui-session__actions",
													children: [/* @__PURE__ */ W("button", {
														className: "paui-session__action",
														type: "button",
														ref: O.current === e.sessionId ? ee : void 0,
														"aria-controls": d ? `${s.instance}-session-menu` : void 0,
														"aria-expanded": d,
														"aria-haspopup": "menu",
														"aria-label": n.sessionActions(c),
														disabled: p,
														onClick: (t) => {
															if (t.stopPropagation(), d) {
																se(!0);
																return;
															}
															x(t.currentTarget, e.sessionId);
														},
														children: /* @__PURE__ */ W(Dc, {})
													}), a && /* @__PURE__ */ W(F, { children: [/* @__PURE__ */ W("button", {
														type: "button",
														className: "paui-session__action paui-session__quick",
														"aria-label": e.archived ? n.restoreSession : n.archiveSession,
														title: e.archived ? n.restoreSession : n.archiveSession,
														disabled: p,
														onClick: () => void ue(e, { archived: !e.archived }),
														children: /* @__PURE__ */ W(kc, {})
													}), /* @__PURE__ */ W("button", {
														type: "button",
														className: "paui-session__action paui-session__quick",
														"aria-label": e.pinned ? n.unpinSession : n.pinSession,
														"aria-pressed": !!e.pinned,
														title: e.pinned ? n.unpinSession : n.pinSession,
														disabled: p,
														onClick: () => void ue(e, { pinned: !e.pinned }),
														children: /* @__PURE__ */ W(Oc, {})
													})] })]
												}) : null
											]
										})]
									}, e.sessionId);
								})]
							}, e);
						}),
						t.sessions?.nextCursor ? /* @__PURE__ */ W("button", {
							className: "paui-load-more",
							type: "button",
							disabled: p,
							onClick: () => void le(t.sessions?.nextCursor),
							children: n.loadMore
						}) : null,
						h || i ? /* @__PURE__ */ W("span", {
							className: "paui-error-text",
							role: "alert",
							children: h ?? i
						}) : null
					]
				}),
				j && A && !M && !w && /* @__PURE__ */ W("div", {
					className: "paui-session-preview",
					role: "tooltip",
					style: A.below ? { top: A.y } : { bottom: A.y },
					children: [
						/* @__PURE__ */ W("strong", { children: j.alias || j.title || n.sessionUntitled }),
						j.cwd && /* @__PURE__ */ W("small", { children: j.cwd }),
						j.fullTime && /* @__PURE__ */ W("small", { children: j.fullTime }),
						j.loaded && /* @__PURE__ */ W("small", {
							className: "paui-session-preview__state",
							children: j.loaded.interactionCount ? n.pendingInteractions(j.loaded.interactionCount) : n.sessionPhase(j.loaded.phase)
						})
					]
				}),
				M ? /* @__PURE__ */ W("div", {
					ref: u,
					id: `${s.instance}-session-menu`,
					className: "paui-session-menu",
					onKeyDown: Zn,
					role: "menu",
					"aria-label": n.sessionActions(M.alias || (M.title ?? n.sessionUntitled)),
					style: y ?? { visibility: "hidden" },
					children: [a && /* @__PURE__ */ W(F, { children: [
						/* @__PURE__ */ W("button", {
							ref: d,
							type: "button",
							role: "menuitem",
							onClick: () => void ue(M, { pinned: !M.pinned }),
							children: M.pinned ? n.unpinSession : n.pinSession
						}),
						/* @__PURE__ */ W("button", {
							type: "button",
							role: "menuitem",
							onClick: () => {
								T(M.sessionId), D(M.alias || (M.title ?? "")), se();
							},
							children: n.renameSession
						}),
						/* @__PURE__ */ W("button", {
							type: "button",
							role: "menuitem",
							onClick: () => void ue(M, { archived: !M.archived }),
							children: M.archived ? n.restoreSession : n.archiveSession
						})
					] }), t.capabilities.deleteSession && M.sessionId !== t.sessionId && /* @__PURE__ */ W("button", {
						ref: a ? void 0 : d,
						type: "button",
						role: "menuitem",
						"data-danger": "true",
						"aria-disabled": oe,
						onClick: () => {
							oe || de(M);
						},
						children: [/* @__PURE__ */ W(jc, {}), /* @__PURE__ */ W("span", { children: n.deleteSession })]
					})]
				}) : null
			]
		})
	});
}
function sc(e, t, n) {
	let r = /* @__PURE__ */ new Map();
	for (let t of e.sessions?.sessions ?? []) r.set(t.sessionId, t);
	for (let t of e.loadedSessions) {
		let e = r.get(t.sessionId), n = (Date.parse(e?.updatedAt ?? "") || 0) > (Date.parse(t.updatedAt ?? "") || 0) ? e?.updatedAt : t.updatedAt ?? e?.updatedAt;
		r.set(t.sessionId, {
			...e,
			...t,
			updatedAt: n,
			loaded: t
		});
	}
	for (let [e, n] of t) {
		let t = r.get(e);
		(t || n.pinned || n.archived) && r.set(e, {
			...n,
			...t,
			title: t?.title ?? n.title,
			updatedAt: t?.updatedAt ?? n.updatedAt
		});
	}
	return [...r.values()].filter((e) => !!e.archived === n).map((e) => {
		let t = Date.parse(e.updatedAt ?? "");
		return {
			...e,
			activityTime: t || 0,
			fullTime: Number.isFinite(t) ? bs.format(t) : void 0
		};
	}).sort((e, t) => Number(!!t.pinned) - Number(!!e.pinned) || t.activityTime - e.activityTime);
}
function cc(e) {
	let t = e?.getRootNode();
	return t instanceof Document || t instanceof ShadowRoot ? t.activeElement : document.activeElement;
}
var lc = new to({
	gfm: !0,
	breaks: !0
}), uc = "a[href], button, input, select, textarea, [tabindex]:not([tabindex=\"-1\"])", dc = new Za();
dc.html = ({ text: e }) => mc(e), dc.image = ({ text: e }) => `<span class="paui-markdown-image-alt">${mc(e)}</span>`, dc.checkbox = ({ checked: e }) => e ? "[x] " : "[ ] ", dc.table = function(e) {
	return `<div class="paui-markdown-table">${Za.prototype.table.call(this, e)}</div>`;
}, dc.link = ({ href: e, title: t, tokens: n }) => {
	let r = mc(n.map((e) => e.raw).join(""));
	return hc(e) ? `<a href="${pc(e)}" target="_blank" rel="noopener noreferrer"${t ? ` title="${pc(t)}"` : ""}>${r}</a>` : r;
}, lc.use({ renderer: dc });
function fc(e) {
	let t = lc.parse(e);
	return bi.sanitize(t, {
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
function pc(e) {
	return mc(e).replaceAll("\"", "&quot;").replaceAll("'", "&#39;");
}
function mc(e) {
	return e.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}
function hc(e) {
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
function gc(e) {
	let t = ds.get(e);
	if (t !== void 0) return t;
	let n = ++fs;
	return ds.set(e, n), n;
}
function _c(e) {
	if (e.sessionId) return e.sessionInstanceId ? `${e.sessionId}\u0000${e.sessionInstanceId}` : e.sessionId;
}
function vc(e, t) {
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
function yc(e) {
	return e.some((e) => e.status === "in_progress") ? "in_progress" : e.length && e.every((e) => e.status === "completed") ? "completed" : "pending";
}
function bc(e) {
	switch (e.type) {
		case "tool": return e.status;
		case "plan": return yc(e.entries);
		case "terminal": return e.exited ? "completed" : "in_progress";
		case "message": return e.pending ? "pending" : void 0;
		case "unsupported": return "unsupported";
		case "context":
		case "notice": return;
	}
}
function xc(e, t = Date.now(), n = io.sessionAge) {
	if (!e) return "";
	let r = new Date(e).valueOf();
	if (Number.isNaN(r)) return e;
	let i = 6e4, a = 60 * i, o = 24 * a, s = Math.max(0, t - r);
	return s < i ? n(0, "now") : s < a ? n(Math.floor(s / i), "minute") : s < o ? n(Math.floor(s / a), "hour") : s < 7 * o ? n(Math.floor(s / o), "day") : s < 30 * o ? n(Math.floor(s / (7 * o)), "week") : s < 365 * o ? n(Math.floor(s / (30 * o)), "month") : n(Math.floor(s / (365 * o)), "year");
}
function Sc(e) {
	return typeof e == "object" && !!e && !Array.isArray(e);
}
function Cc({ status: e }) {
	return /* @__PURE__ */ W("span", {
		className: "paui-status",
		"data-status": e,
		children: e.replaceAll("_", " ")
	});
}
function $({ children: e }) {
	return /* @__PURE__ */ W("svg", {
		viewBox: "0 0 20 20",
		"aria-hidden": "true",
		focusable: "false",
		children: e
	});
}
var wc = () => /* @__PURE__ */ W($, { children: /* @__PURE__ */ W("path", { d: "M3 10a7 7 0 1 0 2-4.9M3 3v4h4M10 6v4l3 2" }) }), Tc = () => /* @__PURE__ */ W($, { children: /* @__PURE__ */ W("path", { d: "M4 4h8a3 3 0 0 1 3 3v4a3 3 0 0 1-3 3H8l-4 3v-3a3 3 0 0 1-1-2V7a3 3 0 0 1 3-3M10 7v5M7.5 9.5h5" }) }), Ec = () => /* @__PURE__ */ W($, { children: /* @__PURE__ */ W("path", { d: "m5 5 10 10M15 5 5 15" }) }), Dc = () => /* @__PURE__ */ W($, { children: [
	/* @__PURE__ */ W("circle", {
		cx: "5",
		cy: "10",
		r: "1",
		fill: "currentColor",
		stroke: "none"
	}),
	/* @__PURE__ */ W("circle", {
		cx: "10",
		cy: "10",
		r: "1",
		fill: "currentColor",
		stroke: "none"
	}),
	/* @__PURE__ */ W("circle", {
		cx: "15",
		cy: "10",
		r: "1",
		fill: "currentColor",
		stroke: "none"
	})
] }), Oc = () => /* @__PURE__ */ W($, { children: /* @__PURE__ */ W("path", { d: "m12 3 5 5-2 1-1.5 4-2 2-2.5-3-5 5 4-6-2.5-2.5 2-2 4-1.5z" }) }), kc = () => /* @__PURE__ */ W($, { children: [/* @__PURE__ */ W("rect", {
	x: "3",
	y: "4",
	width: "14",
	height: "3",
	rx: "1"
}), /* @__PURE__ */ W("path", { d: "M4.5 7v9h11V7M8 10h4" })] }), Ac = () => /* @__PURE__ */ W($, { children: /* @__PURE__ */ W("path", { d: "M2.5 6V4.5h6l2 2H17v2.2M2.5 7.5h15l-2 8h-12z" }) }), jc = () => /* @__PURE__ */ W($, { children: /* @__PURE__ */ W("path", { d: "M4 6h12M8 3h4l1 3M6 6l1 11h6l1-11M9 9v5M12 9v5" }) }), Mc = () => /* @__PURE__ */ W("svg", {
	viewBox: "0 0 16 16",
	"aria-hidden": "true",
	focusable: "false",
	children: /* @__PURE__ */ W("path", {
		d: "M8.3125.9802c.3552.0729.6665.224 0.9502.4521.2245.1807.4676.4256.7168.6748L14.707 6.8347 13.293 8.2487 9 3.9558v11.0859H7V3.9558L2.707 8.2487 1.293 6.8347l4.7275-4.7276c.2492-.2492.4923-.4941.7168-.6748.2393-.1924.5471-.3883.9502-.4521.2098-.0332.4156-.025.625 0Z",
		fill: "currentColor"
	})
}), Nc = () => /* @__PURE__ */ W("svg", {
	viewBox: "0 0 16 16",
	"aria-hidden": "true",
	focusable: "false",
	children: /* @__PURE__ */ W("rect", {
		x: "3",
		y: "3",
		width: "10",
		height: "10",
		rx: "3",
		fill: "currentColor"
	})
}), Pc = () => /* @__PURE__ */ W($, { children: /* @__PURE__ */ W("path", { d: "m5 8 5 5 5-5" }) }), Fc = () => /* @__PURE__ */ W($, { children: /* @__PURE__ */ W("path", { d: "m12.5 4.5-5 5 5 5" }) }), Ic = () => /* @__PURE__ */ W("svg", {
	viewBox: "0 0 14 14",
	"aria-hidden": "true",
	focusable: "false",
	children: /* @__PURE__ */ W("path", { d: "m4 5.5 3 3 3-3" })
}), Lc = () => /* @__PURE__ */ W("svg", {
	viewBox: "0 0 14 14",
	"aria-hidden": "true",
	focusable: "false",
	children: /* @__PURE__ */ W("path", { d: "m3 7 2.5 2.5L11 4" })
}), Rc = () => /* @__PURE__ */ W($, { children: /* @__PURE__ */ W("path", { d: "M12.5 4.2a4 4 0 0 0-5 5L3 13.7 6.3 17l4.5-4.5a4 4 0 0 0 5-5l-2.3 2.3-3.3-3.3 2.3-2.3Z" }) }), zc = () => /* @__PURE__ */ W($, { children: [
	/* @__PURE__ */ W("circle", {
		cx: "10",
		cy: "5",
		r: "2"
	}),
	/* @__PURE__ */ W("circle", {
		cx: "5",
		cy: "14",
		r: "2"
	}),
	/* @__PURE__ */ W("circle", {
		cx: "15",
		cy: "14",
		r: "2"
	}),
	/* @__PURE__ */ W("path", { d: "m8.8 6.7-2.6 5.6M11.2 6.7l2.6 5.6M7 14h6" })
] }), Bc = () => /* @__PURE__ */ W($, { children: /* @__PURE__ */ W("path", { d: "M5 5h5v5M10 5 4.5 10.5M9 9h6v6H9" }) }), Vc = () => /* @__PURE__ */ W($, { children: /* @__PURE__ */ W("path", { d: "M6 5h10M6 10h10M6 15h10M3 5h.01M3 10h.01M3 15h.01" }) }), Hc = () => /* @__PURE__ */ W("svg", {
	className: "paui-think-icon",
	viewBox: "0 0 14 14",
	"aria-hidden": "true",
	focusable: "false",
	children: [/* @__PURE__ */ W("path", {
		d: "M7.06431 5.93342C7.68763 5.93342 8.19307 6.43904 8.19322 7.06233C8.19322 7.68573 7.68772 8.19123 7.06431 8.19123C6.44099 8.19113 5.9354 7.68567 5.9354 7.06233C5.93555 6.43911 6.44108 5.93353 7.06431 5.93342Z",
		fill: "currentColor"
	}), /* @__PURE__ */ W("path", {
		fillRule: "evenodd",
		clipRule: "evenodd",
		d: "M8.6815.963693c1.4354-.516674 2.9451-.588864 3.8818.347657.9367.9367.8644 2.44641.3477 3.88184-.1984.55112-.4724 1.12477-.8145 1.7041.4004.64909.7176 1.29289.9395 1.90918.5167 1.43543.5891 2.94513-.3477 3.88183-.9367.9367-2.4463.8644-3.8818.3477-.61628-.2219-1.26009-.5391-1.90918-.9395-.57935.3421-1.15297.616-1.7041.8145-1.43545.5166-2.94512.589-3.88184-.3477-.936521-.9367-.864331-2.4465-.347656-3.88188.208126-.57809.499486-1.18084.865236-1.78907-.30714-.53529-.55661-1.06415-.74024-1.57421C.572068 3.88278.499714 2.37306 1.43638 1.43635c.9367-.936695 2.44642-.864306 3.88184-.34766.51006.18363 1.03893.43311 1.57421.74024.60823-.36575 1.21098-.65712 1.78907-.865237ZM11.3573 8.01154c-.449.61099-.9672 1.21719-1.54787 1.79786-.58066.5807-1.18688 1.0989-1.79785 1.5478.41412.2269.81712.4115 1.20117.5499 1.33285.4797 2.21185.3476 2.62695-.0674.4151-.4151.5472-1.2941.0674-2.62698-.1383-.38406-.323-.78704-.5498-1.20118ZM2.56529 8.02912c-.19185.3641-.35034.71884-.47266 1.0586-.47972 1.33268-.34751 2.21178.06738 2.62698.41504.415 1.29414.5471 2.62696.0674.3236-.1165.66089-.2657 1.00683-.4454-.5448-.4144-1.08458-.8834-1.60351-1.4023-.61451-.61453-1.1586-1.25807-1.625-1.90528Zm4.34179-4.78222c-.66643.45789-1.34248 1.01631-1.99316 1.66699-.65067.65067-1.2091 1.32674-1.66699 1.99316.47981.7262 1.08084 1.46754 1.79199 2.17871.61051.61051 1.24291 1.14074 1.86914 1.58204.68562-.4653 1.38274-1.03704 2.05273-1.70704.67001-.67001 1.24171-1.3671 1.70701-2.05273-.4413-.62623-.97149-1.25863-1.58201-1.86914-.71117-.71116-1.45251-1.31217-2.17871-1.79199Zm4.80762-1.08692c-.4151-.41489-1.2943-.5471-2.62695-.06738-.3394.12219-.69393.28011-1.05762.47168.64715.46637 1.28982 1.01152 1.9043 1.62598.51897.51894.98787 1.0587 1.40237 1.60351.1796-.34592.3288-.68325.4453-1.00683.4797-1.33278.3476-2.21192-.0674-2.62696ZM4.91197 2.2176c-1.33275-.47972-2.21193-.34765-2.62696.06738-.415.41505-.5471 1.29422-.06738 2.62696.09946.27628.22349.56233.36914.85546.43254-.5787.92797-1.1516 1.47852-1.70214.55055-.55056 1.12343-1.04598 1.70214-1.47852-.29312-.14564-.57919-.26968-.85546-.36914Z",
		fill: "currentColor"
	})]
}), Uc = () => /* @__PURE__ */ W($, { children: /* @__PURE__ */ W("path", { d: "M5 3h10v14H5zM8 7h4M8 10h4" }) }), Wc = () => /* @__PURE__ */ W($, { children: [/* @__PURE__ */ W("circle", {
	cx: "8.5",
	cy: "8.5",
	r: "5.5"
}), /* @__PURE__ */ W("path", { d: "m12.5 12.5 4 4" })] }), Gc = () => /* @__PURE__ */ W($, { children: /* @__PURE__ */ W("path", { d: "m4 6 4 4-4 4M10 14h6" }) }), Kc = () => /* @__PURE__ */ W($, { children: /* @__PURE__ */ W("path", { d: "M10 2 16 5v5c0 4-2.5 6.5-6 8-3.5-1.5-6-4-6-8V5l6-3Zm-2 8 1.5 1.5L13 8" }) }), qc = () => /* @__PURE__ */ W($, { children: /* @__PURE__ */ W("path", { d: "M8 12 12 8M6.5 13.5l-1 1a3 3 0 0 1-4-4l3-3a3 3 0 0 1 4 0M13.5 6.5l1-1a3 3 0 0 1 4 4l-3 3a3 3 0 0 1-4 0" }) }), Jc = () => /* @__PURE__ */ W($, { children: /* @__PURE__ */ W("path", { d: "M5 2h7l4 4v12H5V2Zm7 0v5h4" }) }), Yc = () => /* @__PURE__ */ W($, { children: /* @__PURE__ */ W("path", { d: "M5 3v14M3 5l2-2 2 2M15 17V3M13 15l2 2 2-2M9 7h3M9 13h3" }) }), Xc = () => /* @__PURE__ */ W($, { children: /* @__PURE__ */ W("path", { d: "M6 5h10v10H6zM3 8v9h9" }) }), Zc = () => /* @__PURE__ */ W($, { children: [/* @__PURE__ */ W("circle", {
	cx: "10",
	cy: "10",
	r: "7"
}), /* @__PURE__ */ W("path", { d: "M10 9v5M10 6h.01" })] }), Qc = () => /* @__PURE__ */ W($, { children: [/* @__PURE__ */ W("path", { d: "M10 2 19 18H1L10 2Z" }), /* @__PURE__ */ W("path", { d: "M10 7v5M10 15h.01" })] }), $c = () => /* @__PURE__ */ W($, { children: /* @__PURE__ */ W("path", { d: "m10 2 1.5 4.5L16 8l-4.5 1.5L10 14l-1.5-4.5L4 8l4.5-1.5L10 2ZM15.5 13l.7 2.3 2.3.7-2.3.7-.7 2.3-.7-2.3-2.3-.7 2.3-.7.7-2.3Z" }) }), el = () => /* @__PURE__ */ W($, { children: /* @__PURE__ */ W("path", { d: "M4 3h12v14H4zM7 7h6M7 10h6M7 13h3" }) }), tl = ".pretty-aui-standalone-root{box-sizing:border-box;width:100%;min-width:0;height:100%;min-height:0}.pretty-aui-standalone-root>.pretty-aui{height:100%;min-height:0}.pretty-aui{--paui-default-background:#fff;--paui-default-surface:#f7f8fa;--paui-default-surface-raised:#fff;--paui-default-user-bubble:#edf3fe;--paui-default-text:#0f1115;--paui-default-text-muted:#667085;--paui-default-border:#e5e7eb;--paui-default-accent:#4176e6;--paui-default-on-accent:#fff;--paui-default-accent-soft:#edf3fe;--paui-default-danger:#c63d4f;--paui-default-warning:#a86610;--paui-default-success:#24845b;--paui-default-action-hover:#679efe;--paui-default-flow-title:#61666b;--paui-default-flow-copy:#81858c;--paui-default-flow-caption:#adb2b8;--paui-background:var(--pretty-aui-color-background,var(--paui-default-background));--paui-surface:var(--pretty-aui-color-surface,var(--paui-default-surface));--paui-surface-raised:var(--pretty-aui-color-surface-raised,var(--paui-default-surface-raised));--paui-user-bubble:var(--pretty-aui-color-user-bubble,var(--paui-default-user-bubble));--paui-text:var(--pretty-aui-color-text,var(--paui-default-text));--paui-text-muted:var(--pretty-aui-color-text-muted,var(--paui-default-text-muted));--paui-border:var(--pretty-aui-color-border,var(--paui-default-border));--paui-accent:var(--pretty-aui-color-accent,var(--paui-default-accent));--paui-on-accent:var(--pretty-aui-color-on-accent,var(--paui-default-on-accent));--paui-accent-soft:var(--pretty-aui-color-accent-soft,var(--paui-default-accent-soft));--paui-danger:var(--pretty-aui-color-danger,var(--paui-default-danger));--paui-warning:var(--pretty-aui-color-warning,var(--paui-default-warning));--paui-success:var(--pretty-aui-color-success,var(--paui-default-success));--paui-action-hover:var(--paui-default-action-hover);--paui-flow-title:var(--pretty-aui-color-text-muted,var(--paui-default-flow-title));--paui-flow-copy:var(--pretty-aui-color-text-muted,var(--paui-default-flow-copy));--paui-flow-caption:var(--pretty-aui-color-text-muted,var(--paui-default-flow-caption));--paui-sans:var(--pretty-aui-font-sans,Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif);--paui-mono:var(--pretty-aui-font-mono,ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace);--paui-shadow-raised:var(--pretty-aui-shadow-raised,0 4px 12px 0 #00000005, 0 2px 8px 0 #0000000a);--paui-content-width:var(--pretty-aui-content-max-width,748px);--paui-composer-width:var(--pretty-aui-composer-max-width,780px);--paui-gutter:var(--pretty-aui-gutter,16px);box-sizing:border-box;width:100%;height:var(--pretty-aui-height,680px);min-width:0;min-height:var(--pretty-aui-min-height,420px);border:1px solid var(--paui-border);color:var(--paui-text);--lightningcss-light:initial;--lightningcss-dark: ;color-scheme:light;background:var(--paui-background);contain:layout style;font-family:var(--paui-sans);text-align:left;isolation:isolate;border-radius:14px;flex-direction:column;font-size:14px;line-height:1.5;display:flex;position:relative;overflow:clip;container:pretty-aui/inline-size}.pretty-aui[data-scheme=dark]{--paui-default-background:#151517;--paui-default-surface:#232324;--paui-default-surface-raised:#2c2c2e;--paui-default-user-bubble:#2c2c2e;--paui-default-text:#f9fafb;--paui-default-text-muted:#a4a7ae;--paui-default-border:#343438;--paui-default-accent:#679efe;--paui-default-on-accent:#0f1115;--paui-default-accent-soft:#202c43;--paui-default-danger:#f08a96;--paui-default-warning:#e6ab5e;--paui-default-success:#65c99c;--paui-default-action-hover:#8ab4ff;--paui-default-flow-title:#cfd3d6;--paui-default-flow-copy:#adb2b8;--paui-default-flow-caption:#81858c;--lightningcss-light: ;--lightningcss-dark:initial;color-scheme:dark}@media (prefers-color-scheme:dark){.pretty-aui[data-scheme=system]{--paui-default-background:#151517;--paui-default-surface:#232324;--paui-default-surface-raised:#2c2c2e;--paui-default-user-bubble:#2c2c2e;--paui-default-text:#f9fafb;--paui-default-text-muted:#a4a7ae;--paui-default-border:#343438;--paui-default-accent:#679efe;--paui-default-on-accent:#0f1115;--paui-default-accent-soft:#202c43;--paui-default-danger:#f08a96;--paui-default-warning:#e6ab5e;--paui-default-success:#65c99c;--paui-default-action-hover:#8ab4ff;--paui-default-flow-title:#cfd3d6;--paui-default-flow-copy:#adb2b8;--paui-default-flow-caption:#81858c;--lightningcss-light: ;--lightningcss-dark:initial;color-scheme:dark}}.pretty-aui *,.pretty-aui :before,.pretty-aui :after{box-sizing:border-box}.pretty-aui button,.pretty-aui input,.pretty-aui select,.pretty-aui textarea{color:inherit;font:inherit}.pretty-aui button{cursor:pointer}.pretty-aui :is(button,input,select,textarea):disabled{cursor:not-allowed;opacity:.46}.pretty-aui :is(button,input,select,textarea,summary,a,.paui-body,.paui-context-injection__body):focus-visible{outline:2px solid var(--paui-accent);outline-offset:2px}@media (forced-colors:none){.pretty-aui :is(.paui-model__panel,.paui-session__rename) input:focus-visible{border-color:var(--paui-text-muted);outline:none}}.pretty-aui svg{fill:none;stroke:currentColor;stroke-linecap:round;stroke-linejoin:round;stroke-width:1.6px;flex:none;width:18px;height:18px}.paui-header{z-index:4;border-bottom:1px solid var(--paui-border);background:color-mix(in srgb, var(--paui-background) 94%, transparent);-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px);justify-content:space-between;align-items:center;min-width:0;min-height:56px;padding:10px 14px 10px 18px;display:flex}.pretty-aui[data-surface=sidebar] .paui-header{min-height:48px;padding:7px 8px 7px 12px}.paui-identity,.paui-header__actions,.paui-interaction__actions,.paui-config{align-items:center;display:flex}.paui-identity{flex:auto;gap:10px;min-width:0}.paui-identity>div{min-width:0;display:grid}.paui-identity strong{letter-spacing:-.01em;text-overflow:ellipsis;white-space:nowrap;font-size:13px;font-weight:600;overflow:hidden}.paui-lineage{min-width:0;display:grid}.paui-lineage__titles{white-space:nowrap;align-items:center;gap:6px;min-width:0;display:flex}.paui-lineage__titles strong{text-overflow:ellipsis;min-width:0;overflow:hidden}.paui-lineage__ancestor{min-width:0;color:var(--paui-flow-caption);align-items:center;gap:6px;display:inline-flex}.paui-lineage__ancestor button{max-width:144px;color:var(--paui-text-muted);text-overflow:ellipsis;white-space:nowrap;background:0 0;border:0;padding:0;font-size:13px;overflow:hidden}.paui-lineage__ancestor button:hover:not(:disabled){color:var(--paui-text)}.paui-lineage__back{background:0 0;border:0;border-radius:7px;place-items:center;width:28px;height:28px;padding:0;display:none}.paui-lineage__back:hover:not(:disabled){background:var(--paui-surface)}.paui-lineage__back svg{width:16px;height:16px}.paui-protocol{color:var(--paui-text-muted);font-family:var(--paui-mono);letter-spacing:.02em;text-overflow:ellipsis;text-transform:uppercase;white-space:nowrap;font-size:10px;overflow:hidden}.pretty-aui[data-surface=sidebar] .paui-protocol{display:none}.paui-presence{border:2px solid var(--paui-background);background:var(--paui-text-muted);width:9px;height:9px;box-shadow:0 0 0 1px var(--paui-border);border-radius:50%;flex:none}.paui-presence[data-phase=idle]{background:var(--paui-success)}.paui-presence:is([data-phase=running],[data-phase=awaiting_user],[data-phase=cancelling]){background:var(--paui-accent);box-shadow:0 0 0 1px var(--paui-accent), 0 0 0 4px var(--paui-accent-soft)}.paui-header__actions{flex:none;gap:2px}.paui-icon-button,.paui-send,.paui-to-bottom{background:0 0;border:0;border-radius:10px;place-items:center;width:34px;height:34px;padding:0;display:inline-grid}.paui-icon-button:hover:not(:disabled){background:var(--paui-surface)}.paui-body{min-width:0;min-height:0;padding:24px var(--paui-gutter) 0;overscroll-behavior:contain;scrollbar-color:var(--paui-border) transparent;scrollbar-gutter:stable;flex:auto;position:relative;overflow:hidden auto}.paui-transcript{width:100%;max-width:var(--paui-content-width);gap:28px;margin:0 auto;padding-bottom:24px;display:grid}.paui-turn{gap:16px;min-width:0;display:grid}.paui-message{flex-direction:column;min-width:0;display:flex}.paui-message[data-role=user]{align-items:flex-end;gap:6px}.paui-message__bubble{min-width:0}.paui-message[data-role=user] .paui-message__bubble{background:var(--paui-user-bubble);border-radius:22px;max-width:min(525px,82%);padding:10px 16px}.paui-message[data-role=user][data-pending=true]{opacity:.68}.paui-message__label{display:none}.paui-message__content>:first-child,.paui-markdown>:first-child{margin-top:0}.paui-message__content>:last-child,.paui-markdown>:last-child{margin-bottom:0}.paui-markdown{overflow-wrap:anywhere;min-width:0;font-size:16px;line-height:28px}.paui-message[data-role=user] .paui-markdown{font-size:16px;line-height:24px}.paui-message__actions{align-items:center;gap:10px;height:28px;display:flex}.paui-message[data-role=assistant] .paui-message__actions{margin-top:16px;margin-left:-6px}.paui-message__action{width:28px;height:28px;color:var(--paui-text-muted);background:0 0;border:0;border-radius:50%;place-items:center;padding:6px;display:inline-grid}.pretty-aui .paui-message__action svg{width:16px;height:16px}.paui-message__action:hover{color:var(--paui-text);background:var(--paui-surface)}.paui-message__time{color:var(--paui-text-muted);white-space:nowrap;font-size:14px;line-height:24px}.paui-message__time--start{padding-right:12px}.paui-message__time--end{padding-left:12px}.paui-markdown :is(p,ul,ol,pre,blockquote){margin:.72em 0}.paui-markdown :is(h1,h2,h3,h4){letter-spacing:-.015em;margin:1.15em 0 .45em;font-size:1em;font-weight:650}.paui-markdown :is(code),.paui-url,.paui-terminal pre,.paui-diff pre,.paui-resource pre{font-family:var(--paui-mono);font-size:.84em}.paui-markdown :not(pre)>code{background:var(--paui-surface);border-radius:5px;padding:.14em .35em}.paui-markdown pre,.paui-terminal pre,.paui-diff pre,.paui-resource pre{border:1px solid var(--paui-border);background:var(--paui-surface);white-space:pre;border-radius:9px;max-width:100%;padding:12px 14px;line-height:1.55;overflow:auto}.paui-markdown-table{box-sizing:border-box;border:1px solid var(--paui-border);scrollbar-color:var(--paui-border) transparent;border-radius:9px;max-width:100%;margin:.72em 0;overflow-x:auto}.paui-markdown-table table{border-collapse:collapse;width:max-content;min-width:100%;font-size:.9em;line-height:1.5}.paui-markdown-table :is(th,td){border-right:1px solid var(--paui-border);border-bottom:1px solid var(--paui-border);overflow-wrap:normal;vertical-align:top;min-width:8rem;padding:8px 10px}.paui-markdown-table th{background:var(--paui-surface);font-weight:650}.paui-markdown-table [align=left]{text-align:left}.paui-markdown-table [align=center]{text-align:center}.paui-markdown-table [align=right]{text-align:right}.paui-markdown-table tr:last-child td{border-bottom:0}.paui-markdown-table :is(th,td):last-child{border-right:0}.paui-markdown a,.paui-resource{color:var(--paui-accent);-webkit-text-decoration-color:color-mix(in srgb, var(--paui-accent) 45%, transparent);text-decoration-color:color-mix(in srgb, var(--paui-accent) 45%, transparent);text-underline-offset:3px}.paui-activities{gap:16px;min-width:0;display:grid}.paui-notice-group{gap:6px;min-width:0;display:grid}.paui-activity{min-width:0}.paui-host-notice{min-width:0;color:var(--paui-text-muted);overflow-wrap:anywhere;align-items:flex-start;gap:7px;padding:2px 0;font-size:13px;line-height:20px;display:flex}.paui-activity[data-kind=notice][data-level=error] .paui-host-notice{color:var(--paui-danger)}.paui-host-notice__icon{flex:none;place-items:center;width:16px;height:20px;display:inline-grid}.paui-host-notice__icon svg{width:14px;height:14px}.paui-thought,.paui-disclosure,.paui-diff,.paui-resource{min-width:0}.paui-thought>summary,.paui-disclosure>summary,.paui-diff>summary,.paui-resource>summary{min-height:28px;color:var(--paui-text-muted);cursor:pointer;border-radius:6px;align-items:center;gap:7px;font-size:13px;line-height:20px;list-style:none;display:flex}.paui-thought>summary:hover,.paui-disclosure>summary:hover{color:color-mix(in srgb, var(--paui-text) 78%, var(--paui-text-muted))}.pretty-aui summary::-webkit-details-marker{display:none}.paui-thought>summary svg,.paui-disclosure>summary svg,.paui-diff>summary svg,.paui-resource>summary svg{width:15px;height:15px}.paui-thought__body,.paui-disclosure__body{color:var(--paui-text-muted);padding:4px 0 4px 22px;font-size:14px;line-height:24px}.pretty-aui .paui-flow-summary{align-items:center;gap:0;min-width:0;height:24px;min-height:24px;line-height:24px;display:flex;position:relative;overflow:hidden}.paui-flow-leading{width:16px;height:16px;color:var(--paui-flow-copy);flex:none;justify-content:center;align-items:center;margin-right:6px;display:inline-flex;position:relative}.paui-flow-icon,.paui-flow-chevron{justify-content:center;align-items:center;transition:opacity .1s;display:inline-flex}.paui-flow-chevron{opacity:0;position:absolute;inset:0}.pretty-aui .paui-flow-leading svg{width:14px;height:14px}.pretty-aui .paui-flow-leading .paui-think-icon{fill:currentColor;stroke:none}.paui-flow-summary:hover .paui-flow-icon,.paui-thought[open] .paui-flow-icon,.paui-tool[open] .paui-flow-icon,.paui-context-injection[open] .paui-flow-icon{opacity:0}.paui-flow-summary:hover .paui-flow-chevron,.paui-thought[open] .paui-flow-chevron,.paui-tool[open] .paui-flow-chevron,.paui-context-injection[open] .paui-flow-chevron{opacity:1}.paui-flow-title{color:var(--paui-flow-title);flex:none;font-size:14px;font-weight:400;line-height:24px}.paui-flow-separator{background:var(--paui-flow-caption);border-radius:1px;flex:none;width:2px;height:2px;margin:0 8px}.paui-flow-preview{min-width:0;color:var(--paui-flow-copy);text-overflow:ellipsis;white-space:nowrap;flex:auto;font-size:14px;line-height:24px;overflow:hidden}.paui-flow-preview[data-follow-end=true]{text-overflow:clip}.paui-context-injection__body{box-sizing:border-box;width:calc(100% - 22px);max-height:141px;color:var(--paui-text-muted);background:var(--paui-surface);font:400 11px/16px var(--paui-mono);scrollbar-color:var(--paui-border) transparent;border-radius:8px;margin:4px 0 0 22px;padding:10px 12px 12px;overflow:auto}.paui-context-injection__body>*+*{margin-top:8px}.paui-context-block{gap:4px;min-width:0;display:grid}.paui-context-meta{min-width:0;color:var(--paui-text-muted);overflow-wrap:anywhere;flex-wrap:wrap;gap:4px 10px;display:flex}.paui-context-meta>span+span{color:var(--paui-flow-caption)}.paui-context-text{color:var(--paui-flow-copy);font:inherit;overflow-wrap:anywhere;white-space:pre-wrap;margin:0}.paui-context-identifier,.paui-context-truncated{color:var(--paui-flow-caption);overflow-wrap:anywhere}.paui-subagent-row{align-items:flex-start;gap:4px;width:100%;min-width:0;min-height:24px;display:flex}.paui-subagent{flex:auto;min-width:0}.paui-subagent-status{color:var(--paui-flow-caption);white-space:nowrap;flex:none;align-items:center;gap:8px;margin-left:12px;font-size:11px;line-height:24px;display:inline-flex}.paui-subagent-status__ongoing{align-items:center;gap:5px;display:inline-flex}.paui-subagent-status__spinner,.paui-session__spinner{border:1.5px solid color-mix(in srgb, var(--paui-accent) 28%, transparent);border-top-color:var(--paui-accent);border-radius:50%;width:9px;height:9px;animation:.8s linear infinite paui-subagent-spin}.paui-subagent-status[data-status=failed],.paui-subagent-status[data-status=cancelled],.paui-subagent:is([data-state=failed],[data-state=cancelled]) .paui-flow-leading{color:var(--paui-danger)}.paui-subagent-open{width:24px;height:24px;color:var(--paui-flow-copy);background:0 0;border:0;border-radius:6px;flex:none;place-items:center;padding:0;display:inline-grid}.paui-subagent-open:hover:not(:disabled){color:var(--paui-text);background:var(--paui-surface)}.paui-subagent-open svg{width:14px;height:14px}.paui-subagent[open] .paui-flow-icon{opacity:0}.paui-subagent[open] .paui-flow-chevron{opacity:1}@keyframes paui-subagent-spin{to{transform:rotate(360deg)}}.paui-thought[open] .paui-flow-separator,.paui-thought[open] .paui-flow-preview{display:none}.paui-tool[data-state=failed] .paui-flow-leading{color:var(--paui-danger)}.paui-thought[data-running=true]>.paui-flow-summary:after,.paui-tool:is([data-state=pending],[data-state=in_progress])>.paui-flow-summary:after{inset-block:0;background:linear-gradient(90deg, transparent 0%, color-mix(in srgb, var(--paui-background) 60%, transparent) 55%, transparent 100%);content:\"\";pointer-events:none;width:300px;animation:2.6s ease-out infinite paui-flow-sweep;position:absolute;left:0}@keyframes paui-flow-sweep{0%{left:-300px}90%,to{left:100%}}@media (prefers-reduced-motion:reduce){.paui-thought[data-running=true]>.paui-flow-summary:after,.paui-tool:is([data-state=pending],[data-state=in_progress])>.paui-flow-summary:after{animation:none}.paui-subagent-status__spinner,.paui-session__spinner{border-color:var(--paui-accent);background:var(--paui-accent);animation:none}}.paui-status{color:var(--paui-text-muted);font-family:var(--paui-mono);letter-spacing:.04em;text-transform:uppercase;margin-left:auto;font-size:9px}.paui-status:is([data-status=failed],[data-status=cancelled]){color:var(--paui-danger)}.paui-plan__list{gap:6px;margin:4px 0 0;padding:4px 0 4px 22px;list-style:none;display:grid}.paui-plan__list li{color:var(--paui-text-muted);grid-template-columns:12px 1fr;align-items:start;gap:8px;font-size:13px;line-height:20px;display:grid}.paui-plan__mark{border:1px solid;border-radius:50%;width:7px;height:7px;margin-top:6px}.paui-plan__list li[data-status=completed] .paui-plan__mark{border-color:var(--paui-success);background:var(--paui-success)}.paui-plan__list li[data-status=in_progress]{color:var(--paui-text)}.paui-plan__list li[data-status=in_progress] .paui-plan__mark{border-color:var(--paui-accent);background:var(--paui-accent);box-shadow:inset 0 0 0 2px var(--paui-background)}.paui-media{border-radius:10px;max-width:100%;max-height:420px;margin:10px 0;display:block}.paui-resource{align-items:center;gap:6px;display:inline-flex}.paui-resource svg{width:15px;height:15px}.paui-unsupported,.paui-muted{color:var(--paui-text-muted);font-size:12px}.paui-notice{background:var(--paui-accent-soft);border-radius:9px;align-items:center;gap:10px;padding:10px 12px;display:flex}.paui-notice>div,.paui-error>div{flex:1;min-width:0;display:grid}.paui-notice strong,.paui-error strong{font-size:12px}.paui-notice span,.paui-error span{color:var(--paui-text-muted);font-size:11px}.paui-notice svg,.paui-error svg{width:16px}.paui-empty{max-width:340px;color:var(--paui-text-muted);text-align:center;justify-items:center;margin:clamp(42px,12vh,90px) auto;display:grid}.paui-empty svg{width:24px;height:24px;color:var(--paui-accent);margin-bottom:12px}.paui-empty strong{color:var(--paui-text);letter-spacing:-.01em;font-size:16px;font-weight:600}.paui-empty p{margin:5px 0 0;font-size:12px}.paui-interactions{z-index:3;min-width:0;padding:0 var(--paui-gutter);background:var(--paui-background);gap:8px;display:grid}.paui-interactions:empty{display:none}.paui-error,.paui-interaction,.paui-auth{width:100%;max-width:var(--paui-content-width);border:1px solid var(--paui-border);background:var(--paui-surface);border-radius:12px;gap:11px;margin:0 auto;display:flex}.paui-error{border-color:color-mix(in srgb, var(--paui-danger) 30%, var(--paui-border));align-items:center;padding:10px 12px}.paui-error button,.paui-auth button,.paui-load-more{border:1px solid var(--paui-border);background:var(--paui-background);border-radius:8px;padding:6px 10px;font-size:12px}.paui-interaction{padding:14px}.paui-interaction__icon{width:28px;height:28px;color:var(--paui-accent);background:var(--paui-accent-soft);border-radius:8px;flex:none;place-items:center;display:grid}.paui-interaction__icon svg{width:16px}.paui-interaction__content{flex:1;gap:8px;min-width:0;display:grid}.paui-interaction__content>strong{font-size:13px}.paui-interaction__content>p{color:var(--paui-text-muted);margin:-3px 0 0;font-size:12px}.paui-interaction__actions{flex-wrap:wrap;gap:6px}.paui-button-primary,.paui-button-secondary,.paui-button-ghost{border-radius:8px;min-height:30px;padding:5px 10px;font-size:12px}.paui-button-primary{border:1px solid var(--paui-accent);color:var(--paui-on-accent);background:var(--paui-accent)}.paui-button-secondary{border:1px solid var(--paui-border);background:var(--paui-background)}.paui-button-ghost{color:var(--paui-text-muted);background:0 0;border:1px solid #0000}.paui-url{border:1px solid var(--paui-border);background:var(--paui-background);text-overflow:ellipsis;white-space:nowrap;border-radius:7px;padding:7px 8px;overflow:hidden}.paui-fields{gap:10px;display:grid}.paui-field{color:var(--paui-text-muted);gap:4px;font-size:11px;display:grid}.paui-field input,.paui-field select{border:1px solid var(--paui-border);min-height:34px;color:var(--paui-text);background:var(--paui-background);border-radius:7px;padding:6px 8px}.paui-field small{font-size:10px}.paui-field--check{align-items:center;display:flex}.paui-auth{justify-items:start;padding:16px;display:grid}.paui-auth>div{gap:6px;display:flex}.paui-auth>svg{color:var(--paui-accent)}.paui-composer-wrap{z-index:3;width:100%;padding:36px var(--paui-gutter) 8px;background:linear-gradient(to bottom, color-mix(in srgb, var(--paui-background) 0%, transparent) 0, var(--paui-background) 36px);justify-items:center;gap:6px;display:grid;position:relative}.paui-composer-wrap[data-placement=hero]{transition:top .18s,transform .18s;position:absolute;top:50%;left:0;transform:translateY(-10%)}.paui-composer{width:100%;max-width:var(--paui-composer-width);background:var(--paui-surface-raised);box-shadow:var(--paui-shadow-raised);border:0;border-radius:22px;flex-direction:column;gap:12px;padding:10px 8px 6px 16px;font-size:16px;line-height:24px;transition:box-shadow .12s;display:flex;position:static}.paui-composer__context{scrollbar-width:thin;flex-wrap:wrap;align-items:center;gap:6px;min-width:0;max-height:68px;padding-right:4px;display:flex;overflow-y:auto}.pretty-aui .paui-context-add{width:22px;height:22px;color:var(--paui-text-muted);background:0 0;border:0;border-radius:6px;flex:0 0 22px;place-items:center;padding:0;font-size:17px;line-height:1;display:inline-grid}.pretty-aui .paui-context-add:hover:not(:disabled){color:var(--paui-text);background:var(--paui-surface)}.paui-context-chip{border:1px solid var(--paui-border);min-width:0;max-width:min(260px,100% - 28px);color:var(--paui-text);background:var(--paui-background);border-radius:7px;align-items:center;gap:4px;padding:2px 3px 2px 8px;font-size:11px;line-height:18px;display:inline-flex}.paui-context-chip__label{text-overflow:ellipsis;white-space:nowrap;overflow:hidden}.pretty-aui .paui-context-chip button{width:18px;height:18px;color:var(--paui-text-muted);background:0 0;border:0;border-radius:5px;flex:0 0 18px;place-items:center;padding:0;font-size:14px;line-height:1;display:inline-grid}.pretty-aui .paui-context-chip button:hover:not(:disabled){color:var(--paui-text);background:var(--paui-surface)}.paui-composer textarea{resize:none;background:0 0;border:0;outline:0;width:100%;min-height:24px;max-height:336px;padding:2px 0;line-height:24px;overflow-y:auto}.pretty-aui .paui-composer textarea:focus-visible{outline:0}.paui-composer-wrap[data-placement=hero] .paui-composer textarea{min-height:52px}.paui-composer textarea::placeholder{color:var(--paui-text-muted)}.paui-composer__actions{flex-wrap:wrap;align-items:center;gap:4px;width:100%;min-width:0;display:flex}.pretty-aui .paui-send{color:var(--paui-on-accent);background:var(--paui-accent);border-radius:999px;transition:background-color .1s;transform:translateY(-2px)}.pretty-aui .paui-send:hover:not(:disabled){background:var(--paui-action-hover)}.pretty-aui .paui-send:disabled{opacity:.4}.pretty-aui .paui-send svg{stroke:none;width:16px;height:16px}.pretty-aui .paui-stop{color:#fff;background:var(--paui-accent)}.paui-config{width:auto;min-height:20px;color:var(--paui-text-muted);gap:8px;font-size:10px}.paui-config label{align-items:center;gap:4px;display:inline-flex}.paui-config__field{min-width:0;position:relative}.pretty-aui .paui-config__trigger{max-width:min(220px,45cqw);min-height:20px;color:var(--paui-text-muted);background:0 0;border:0;border-radius:6px;outline:0;align-items:center;gap:3px;padding:1px 4px;font-size:10px;line-height:16px;text-decoration:none;display:inline-flex}.paui-config__trigger>span{text-overflow:ellipsis;white-space:nowrap;min-width:0;overflow:hidden}.pretty-aui .paui-config__trigger>svg{width:12px;height:12px;color:var(--paui-text-muted);transition:transform .12s}.pretty-aui .paui-config__trigger[aria-expanded=true]>svg{transform:rotate(180deg)}.pretty-aui .paui-config__trigger:hover:not(:disabled),.pretty-aui .paui-config__trigger:focus-visible,.pretty-aui .paui-config__trigger[aria-expanded=true]{color:var(--paui-text-muted);background:var(--paui-surface);outline:0;text-decoration:none}.paui-config__listbox,.paui-composer-menu__panel{--paui-config-scrollbar:color-mix(in srgb, var(--paui-text-muted) 34%, transparent);--paui-config-scrollbar-hover:color-mix(in srgb, var(--paui-text-muted) 56%, transparent)}.paui-config__listbox{z-index:20;overscroll-behavior:contain;width:max-content;min-width:min(220px,100cqw - 32px);max-width:min(360px,100cqw - 32px);max-height:min(320px,100vh - 96px);color:var(--paui-text);background:var(--paui-surface-raised);box-shadow:0 16px 40px #0000001f, var(--paui-shadow-raised);border:0;border-radius:12px;padding:4px;font-size:12px;line-height:20px;position:absolute;bottom:calc(100% + 8px);left:0;overflow:hidden auto}@supports not selector(::-webkit-scrollbar){:is(.paui-config__listbox,.paui-composer-menu__panel){scrollbar-width:thin;scrollbar-color:var(--paui-config-scrollbar) transparent}}:is(.paui-config__listbox,.paui-composer-menu__panel)::-webkit-scrollbar{width:8px;height:8px}:is(.paui-config__listbox,.paui-composer-menu__panel)::-webkit-scrollbar-track{background:0 0}:is(.paui-config__listbox,.paui-composer-menu__panel)::-webkit-scrollbar-corner{background:0 0}:is(.paui-config__listbox,.paui-composer-menu__panel)::-webkit-scrollbar-thumb{background:var(--paui-config-scrollbar);background-clip:padding-box;border:2px solid #0000;border-radius:999px}:is(.paui-config__listbox,.paui-composer-menu__panel)::-webkit-scrollbar-thumb:hover{background:var(--paui-config-scrollbar-hover);background-clip:padding-box}.pretty-aui .paui-config__option{width:100%;min-height:32px;color:var(--paui-text);text-align:left;background:0 0;border:0;border-radius:8px;outline:0;align-items:center;gap:8px;padding:6px 8px;display:flex}.paui-config__option>span:first-child{text-overflow:ellipsis;white-space:nowrap;flex:auto;min-width:0;overflow:hidden}.pretty-aui .paui-config__option[data-active=true],.pretty-aui .paui-config__option:focus-visible,.pretty-aui .paui-composer-menu__panel button:is(:focus,:hover):not(:disabled){background:var(--paui-surface);box-shadow:var(--paui-shadow-raised);outline:0}@media (forced-colors:active){.pretty-aui .paui-config__option[data-active=true],.pretty-aui .paui-composer-menu__panel button:focus:not(:disabled){outline-offset:-2px;outline:2px solid highlight}}.pretty-aui .paui-model>.paui-config__trigger{gap:5px;max-width:min(360px,48cqw);min-height:28px;padding:0 5px 0 8px;font-size:13px;line-height:20px}.paui-model__effort{color:var(--paui-text-muted);flex-shrink:10}.paui-model__chevron{width:6px;height:6px;color:var(--paui-text-muted);border:1.5px solid;border-width:0 1.5px 1.5px 0;flex:none;margin:0 3px;display:inline-block;transform:rotate(45deg)}.paui-model>[aria-expanded=true] .paui-model__chevron{transform:rotate(225deg)}.paui-config__listbox.paui-model__panel{flex-direction:column;min-width:min(240px,100cqw - 76px);max-width:min(420px,100cqw - 76px);max-height:min(360px,44cqh);padding:5px;display:flex;overflow:hidden}.paui-model__cell b{flex:none;font-weight:500}.paui-model__cell>span{text-overflow:ellipsis;white-space:nowrap;text-align:end;min-width:0;color:var(--paui-text-muted);flex:1;overflow:hidden}.paui-model__cell .paui-model__chevron{transform:rotate(-45deg)}.paui-model__panel .paui-config__option{min-height:34px;font-size:13px}.pretty-aui .paui-model__panel button:is(:hover,:focus-visible):not(:disabled){background:var(--paui-surface);box-shadow:var(--paui-shadow-raised);outline:0}.paui-model__back,.paui-model__group,.paui-model__choices>small{color:var(--paui-text-muted);padding:5px 8px;font-size:12px;display:block}.paui-model__back{text-align:start;background:0 0;border:none;border-radius:6px}.paui-model__panel input{border:1px solid var(--paui-border);background:var(--paui-background);width:100%;color:var(--paui-text);border-radius:6px;padding:6px 8px}.paui-model__choices{overscroll-behavior:contain;scrollbar-width:thin;scrollbar-color:var(--paui-config-scrollbar) transparent;overflow:auto}.paui-model__group{background:var(--paui-surface-raised);position:sticky;top:0}.paui-config__check{width:16px;height:16px;color:var(--paui-text);flex:0 0 16px;place-items:center;display:inline-grid}.pretty-aui .paui-config__check svg{width:14px;height:14px}.paui-commands{right:var(--paui-gutter);bottom:calc(100% - 30px);left:var(--paui-gutter);max-width:var(--paui-composer-width);overscroll-behavior:contain;border:1px solid var(--paui-border);background:var(--paui-surface-raised);max-height:320px;box-shadow:var(--paui-shadow-raised);border-radius:12px;margin:0 auto;display:grid;position:absolute;overflow:hidden auto}.paui-commands button{border:0;border-bottom:1px solid var(--paui-border);text-align:left;background:0 0;grid-template-columns:minmax(110px,auto) 1fr;gap:10px;padding:8px 10px;display:grid}.paui-commands button:hover,.paui-commands button[aria-selected=true]{background:var(--paui-surface)}.paui-commands button:last-child{border-bottom:0}.paui-commands code{color:var(--paui-accent);font-family:var(--paui-mono);font-size:11px}.paui-commands span{color:var(--paui-text-muted);font-size:11px}.paui-to-bottom{border:1px solid var(--paui-border);background:var(--paui-surface-raised);box-shadow:var(--paui-shadow-raised);border-radius:50%}.paui-to-bottom-row{flex:none;place-items:center;height:46px;display:grid}.paui-drawer-backdrop{z-index:20;background:0 0;justify-content:flex-end;display:flex;position:absolute;inset:0}.paui-drawer{--paui-session-row-height:32px;border-left:1px solid var(--paui-border);background:var(--paui-background);width:min(340px,88%);height:100%;min-height:0;box-shadow:var(--paui-shadow-raised);grid-template-rows:auto minmax(0,1fr);display:grid;position:relative}.paui-drawer>header{border-bottom:1px solid var(--paui-border);justify-content:space-between;align-items:center;min-height:56px;padding:10px 12px 10px 16px;display:flex}.paui-session-list{overscroll-behavior:contain;scrollbar-color:var(--paui-border) transparent;scrollbar-gutter:stable;align-content:start;gap:2px;min-height:0;padding:8px;display:grid;overflow-y:auto}.paui-session{box-sizing:border-box;height:var(--paui-session-row-height);border-radius:8px;grid-template-columns:minmax(0,1fr) auto;align-items:center;padding:0 4px 0 18px;transition:background-color .1s;display:grid}.paui-session:is(:hover,:focus-within,[data-active=true],[data-menu-open=true]){background:var(--paui-surface)}.paui-session-group,.paui-session-switch,.paui-session__rename button{min-height:28px;color:var(--paui-text-muted);background:0 0;border:0;border-radius:6px;align-items:center;gap:6px;padding:3px 8px;font-size:12px;display:inline-flex}.paui-session-group{max-width:100%;color:var(--paui-text)}.paui-session-group>span{text-overflow:ellipsis;white-space:nowrap;overflow:hidden}.paui-session-group svg,.paui-session__select [role=img] svg{width:14px;height:14px;color:var(--paui-text-muted)}.paui-session-switch{margin-inline:auto 4px}.paui-session-switch:hover,.paui-session-group:hover,.paui-session__rename button:hover{background:var(--paui-surface)}.paui-session-preview{z-index:1;width:min(240px,100cqw - 352px);color:var(--paui-text);overflow-wrap:anywhere;pointer-events:none;background:var(--paui-surface-raised);border-radius:10px;gap:6px;padding:12px 14px;font-size:13px;animation:.25s step-end paui-preview-in;display:grid;position:absolute;right:calc(100% + 4px);box-shadow:0 4px 16px #00000024}@keyframes paui-preview-in{0%{opacity:0}to{opacity:1}}.paui-session-preview small{color:var(--paui-text-muted);font-size:12px}.paui-session-preview__state:before{content:\"●\";margin-inline-end:6px}@container pretty-aui (width<=540px){.paui-session-preview{margin-block:var(--paui-session-row-height);width:calc(100% - 16px);right:8px}}.paui-session__select{min-width:0;height:100%;color:var(--paui-text);text-align:left;background:0 0;border:0;align-items:center;gap:4px;padding:0;display:flex}.pretty-aui .paui-session__select:disabled{cursor:default;opacity:1}.paui-session__rename{gap:4px;min-width:0;display:flex}.paui-session__rename input{color:var(--paui-text);background:var(--paui-background);border:1px solid var(--paui-border);border-radius:5px;width:100%;min-width:0;padding:2px 5px}.paui-session__title{text-overflow:ellipsis;white-space:nowrap;flex:1;min-width:0;font-size:14px;font-weight:400;line-height:20px;overflow:hidden;container-type:inline-size}@media (hover:hover) and (prefers-reduced-motion:no-preference){.paui-session:hover .paui-session__title{text-overflow:clip}.paui-session:hover .paui-session__title>span{animation:1.4s ease-in-out .35s forwards paui-session-title-reveal;display:inline-block}}@keyframes paui-session-title-reveal{to{transform:translate(min(0px,100cqw - 100%))}}.paui-session__spinner{flex:none}.paui-session__trailing{place-items:center end;min-width:32px;max-width:152px;display:grid;overflow:hidden}.paui-session__trailing>*{grid-area:1/1}.paui-session__actions{width:0;display:flex;overflow:hidden}.paui-session__meta{pointer-events:none;min-width:0;color:var(--paui-text-muted);text-overflow:ellipsis;white-space:nowrap;align-items:center;font-size:12px;line-height:20px;transition:opacity .1s;display:block;overflow:hidden}.paui-session__action{width:32px;height:32px;color:var(--paui-text-muted);opacity:0;pointer-events:none;background:0 0;border:0;border-radius:5px;flex:none;place-items:center;padding:0;transition:color .1s,opacity .1s;display:inline-grid}.paui-session__action svg{width:16px;height:16px}.paui-session__action:is(:hover,:focus-visible):not(:disabled){color:var(--paui-text);background:color-mix(in srgb, var(--paui-text) 8%, transparent)}@media (hover:hover){.paui-session:is(:hover,:focus-within,[data-menu-open=true]) .paui-session__actions{width:auto}.paui-session[data-has-actions=true]:is(:hover,:focus-within,[data-menu-open=true]) .paui-session__meta{opacity:0}.paui-session[data-has-actions=true]:is(:hover,:focus-within,[data-menu-open=true]) .paui-session__action{opacity:1;pointer-events:auto}}.paui-session-menu{z-index:2;box-sizing:border-box;border:1px solid var(--paui-border);background:var(--paui-surface-raised);width:min(164px,100% - 16px);box-shadow:var(--paui-shadow-raised);border-radius:12px;padding:4px;display:grid;position:absolute}.paui-session-menu>button{width:100%;min-height:34px;color:var(--paui-text);text-align:left;background:0 0;border:0;border-radius:8px;align-items:center;gap:8px;padding:6px 8px;font-size:13px;line-height:20px;display:flex}.paui-session-menu>button span{text-overflow:ellipsis;white-space:nowrap;min-width:0;overflow:hidden}.paui-session-menu>button:hover:not([aria-disabled=true]){background:var(--paui-surface)}.paui-session-menu>button[data-danger]{color:var(--paui-danger)}.paui-session-menu>button[data-danger]:hover:not([aria-disabled=true]){background:color-mix(in srgb, var(--paui-danger) 10%, transparent)}.paui-session-menu>button[aria-disabled=true]{cursor:not-allowed;opacity:.46}.paui-session-menu svg{width:16px;height:16px}@media (hover:none){.paui-session__quick,.paui-session-preview{display:none}.paui-session__actions{width:auto}.paui-session__action{width:32px;height:32px}.paui-session[data-has-actions=true] .paui-session__trailing{gap:4px;max-width:none;display:flex}.paui-session__meta{max-width:152px}.paui-session[data-has-actions=true] .paui-session__action{opacity:1;pointer-events:auto}}@media (prefers-reduced-motion:reduce){.paui-session,.paui-session__action,.paui-session__meta{transition:none}}.paui-usage{max-width:156px;color:var(--paui-text-muted);font-family:var(--paui-mono);text-overflow:ellipsis;white-space:nowrap;font-size:10px;overflow:hidden}.paui-tool-block{box-sizing:border-box;border:1px solid var(--paui-border);width:100%;min-width:0;color:var(--paui-text);background:color-mix(in srgb, var(--paui-surface) 72%, transparent);font:400 12px/20px var(--paui-mono);border-radius:12px;overflow:hidden}.paui-tool-block__banner,.paui-tool-terminal__header,.paui-tool-io__section-header{justify-content:space-between;align-items:flex-start;gap:12px;min-width:0;display:flex}.paui-tool-block__banner{border-bottom:1px solid var(--paui-border);background:color-mix(in srgb, var(--paui-surface-raised) 36%, transparent);padding:9px 14px}.paui-tool-block__label{text-overflow:ellipsis;white-space:nowrap;min-width:0;overflow:hidden}.paui-tool-block__copy,.paui-tool-block__fold{color:var(--paui-text-muted);font:500 12px/20px var(--paui-sans);background:0 0;border:0;padding:0}.paui-tool-block__copy{flex:none}.paui-tool-block__copy:hover,.paui-tool-block__fold:hover{color:var(--paui-text)}.paui-tool-block__fold{border-block:1px solid var(--paui-border);text-align:left;width:100%;padding:5px 14px;display:block}.paui-tool-block__empty{color:var(--paui-text-muted);padding:12px 14px}.paui-tool-terminal__header{scrollbar-color:var(--paui-border) transparent;max-height:152px;padding:9px 14px 9px 30px;overflow:auto}.paui-tool-terminal:not([data-state=running]) .paui-tool-terminal__header{border-bottom:1px solid var(--paui-border)}.paui-tool-terminal__prompt{flex:1;min-width:max-content}.paui-tool-terminal__prompt-line{white-space:pre;align-items:baseline;gap:9px;min-width:0;display:flex;position:relative}.paui-tool-terminal__state{background:var(--paui-success);border-radius:50%;width:7px;height:7px;position:absolute;top:7px;left:-18px}.paui-tool-terminal[data-state=running] .paui-tool-terminal__state{background:var(--paui-accent);box-shadow:0 0 0 3px var(--paui-accent-soft);animation:1.5s ease-in-out infinite paui-pulse}@keyframes paui-pulse{50%{opacity:.48}}.paui-tool-terminal[data-state=failed] .paui-tool-terminal__state{background:var(--paui-danger)}.paui-tool-terminal__cwd{color:var(--paui-text-muted);flex:none}.paui-tool-terminal__command,.paui-tool-read__content,.paui-tool-diff__line{white-space:pre}.paui-tool-terminal__output{box-sizing:border-box;width:100%;max-height:224px;color:var(--paui-text);font:inherit;scrollbar-color:var(--paui-border) transparent;white-space:pre;background:0 0;margin:0;padding:12px 14px 12px 30px;overflow:auto}.paui-tool-terminal[data-state=failed] .paui-tool-terminal__output{color:var(--paui-danger)}.paui-tool-read__body,.paui-tool-diff__body{scrollbar-color:var(--paui-border) transparent;max-height:286px;overflow:auto}.paui-tool-read__line{grid-template-columns:minmax(38px,max-content) max-content;width:max-content;min-width:100%;display:grid}.paui-tool-read__gutter{color:var(--paui-text-muted);text-align:right;-webkit-user-select:none;user-select:none;padding:0 12px 0 8px}.paui-tool-read__content{padding-right:16px}.paui-tool-diff__line{box-sizing:border-box;width:max-content;min-width:100%;padding:0 14px}.paui-tool-diff__line[data-line-kind=add]{color:color-mix(in srgb, var(--paui-success) 88%, var(--paui-text));background:color-mix(in srgb, var(--paui-success) 11%, transparent)}.paui-tool-diff__line[data-line-kind=delete]{color:color-mix(in srgb, var(--paui-danger) 88%, var(--paui-text));background:color-mix(in srgb, var(--paui-danger) 10%, transparent)}.paui-tool-diff__line[data-line-kind=meta]{color:var(--paui-text-muted)}.paui-tool-diff__footer{border-top:1px solid var(--paui-border);color:var(--paui-text-muted);padding:6px 14px;font-size:11px}.paui-tool-io__section{scrollbar-color:var(--paui-border) transparent;max-height:190px;overflow:auto}.paui-tool-io__section-header{z-index:1;color:var(--paui-text-muted);background:var(--paui-surface);font:600 10px/18px var(--paui-sans);letter-spacing:.06em;text-transform:uppercase;padding:7px 14px;position:sticky;top:0}.paui-tool-io__section[data-error=true] .paui-tool-io__section-header,.paui-tool-io__section[data-error=true] .paui-tool-io__content{color:var(--paui-danger)}.paui-tool-io__content{min-width:max-content;padding:8px 14px 12px}.paui-tool-io__content pre{color:inherit;font:inherit;white-space:pre;margin:0}.paui-tool-io__divider{border-top:1px solid var(--paui-border);display:block}.paui-tool-supplementary{margin-top:8px}@media (prefers-reduced-motion:reduce){.paui-tool-terminal[data-state=running] .paui-tool-terminal__state{animation:none}}.paui-load-more{margin-top:6px}.paui-error-text{color:var(--paui-danger);padding:8px;font-size:11px}.paui-sr-only{clip:rect(0, 0, 0, 0);white-space:nowrap;border:0;width:1px;height:1px;padding:0;position:absolute;overflow:hidden}@container pretty-aui (width<=560px){.paui-header{min-height:48px;padding:7px 8px 7px 12px}.paui-identity--child{gap:4px}.paui-identity--child .paui-presence,.paui-lineage__ancestor{display:none}.paui-lineage{align-items:center;display:flex}.paui-lineage__back{display:inline-grid}.paui-lineage__titles{flex:auto;min-width:0}.paui-body{padding-top:18px}.paui-transcript{padding-bottom:18px}.paui-message[data-role=user] .paui-message__bubble{max-width:88%}.paui-markdown{font-size:15px;line-height:25px}.paui-message[data-role=user] .paui-markdown{font-size:15px;line-height:23px}.paui-interaction__actions{align-items:stretch}.paui-button-primary,.paui-button-secondary,.paui-button-ghost{flex:auto}.paui-composer-wrap{padding-left:10px;padding-right:10px}.paui-composer{padding-left:14px}}.pretty-aui[data-surface=sidebar] .paui-identity--child{gap:4px}.pretty-aui[data-surface=sidebar] :is(.paui-identity--child .paui-presence,.paui-lineage__ancestor){display:none}.pretty-aui[data-surface=sidebar] .paui-lineage{align-items:center;display:flex}.pretty-aui[data-surface=sidebar] .paui-lineage__back{display:inline-grid}@container pretty-aui (width<=380px){.paui-identity{gap:7px}.paui-protocol{display:none}.paui-message[data-role=user] .paui-message__bubble{max-width:92%}.paui-interaction{padding:11px}.paui-interaction__icon{display:none}}@media (prefers-reduced-motion:reduce){.pretty-aui *,.pretty-aui :before,.pretty-aui :after{scroll-behavior:auto!important;transition-duration:.01ms!important;animation-duration:.01ms!important;animation-iteration-count:1!important}}.paui-composer-menu{flex-shrink:0}.paui-composer-menu__panel{z-index:20;overscroll-behavior:contain;border:1px solid var(--paui-border);background:var(--paui-surface-raised);max-height:320px;box-shadow:var(--paui-shadow-raised);border-radius:12px;grid-template-columns:minmax(0,1fr);gap:2px;padding:6px;display:grid;position:absolute;bottom:calc(100% + 8px);left:0;right:0;overflow-y:auto}.paui-composer-unit{width:100%;max-width:var(--paui-composer-width);position:relative}.paui-shortcuts{gap:6px;padding:0 4px 5px;display:flex}.pretty-aui .paui-shortcut,.pretty-aui .paui-turn-summary{color:var(--paui-text-muted);background:0 0;border:0;padding:4px 8px;font-size:12px}.pretty-aui .paui-turn-summary{text-align:start;border-bottom:1px solid var(--paui-border);border-radius:0}.paui-composer-spacer{flex:1}.paui-composer__actions>.paui-config__field .paui-config__listbox{left:auto;right:0}.paui-composer-menu__panel small{color:var(--paui-text-muted);font-size:11px}.paui-composer-menu__panel [role=group]>small{padding:6px 10px 2px;display:block}.pretty-aui .paui-composer-menu__panel button{text-align:start;background:0 0;border:0;border-radius:8px;align-items:baseline;gap:18px;width:100%;padding:8px 10px;display:flex}.paui-composer-menu__panel button>:is(span,small){white-space:nowrap;text-overflow:ellipsis;overflow:hidden}.paui-composer-menu__panel button>span:has(+small){flex:none;max-width:55%}.paui-composer-images{flex-wrap:wrap;gap:8px;padding:8px;display:flex}.paui-composer-images img{object-fit:contain;width:48px;height:48px}.paui-composer-images small{flex-basis:100%}", nl = "Acp-Connection-Id", rl = "Acp-Session-Id", il = "text/event-stream", al = "application/json";
r.session_cancel, r.session_close, r.session_delete, r.session_fork, r.session_load, r.session_prompt, r.session_resume, r.session_set_config_option, r.session_set_mode, r.nes_suggest, r.nes_accept, r.nes_reject, r.nes_close, r.document_did_open, r.document_did_change, r.document_did_close, r.document_did_save, r.document_did_focus;
function ol(e) {
	if (!h(e)) return;
	let t = e.sessionId;
	return typeof t == "string" ? t : void 0;
}
function sl(e) {
	return "method" in e ? ol(e.params) : void 0;
}
function cl(e) {
	if (!m(e) || !("result" in e) || !h(e.result)) return;
	let t = e.result.sessionId;
	return typeof t == "string" ? t : void 0;
}
function ll(e) {
	return e.jsonrpc === "2.0" && "id" in e && "method" in e && e.method === r.initialize;
}
function ul(e) {
	if (typeof e == "string") return `string:${e}`;
	if (typeof e == "number") return `number:${e}`;
	if (e === null) return "null";
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/cookie-store.js
var dl = class {
	cookies = /* @__PURE__ */ new Map();
	store(e) {
		for (let t of fl(e)) {
			let e = ml(t);
			e && this.cookies.set(e.name, e.value);
		}
	}
	apply(e) {
		let t = hl(this.cookieHeader(), e.get("Cookie"));
		t && e.set("Cookie", t);
	}
	clear() {
		this.cookies.clear();
	}
	cookieHeader() {
		return this.cookies.size === 0 ? void 0 : Array.from(this.cookies).map(([e, t]) => `${e}=${t}`).join("; ");
	}
};
function fl(e) {
	let t = e.getSetCookie;
	if (typeof t == "function") return t.call(e).flatMap(pl);
	let n = e.get("Set-Cookie");
	return n ? pl(n) : [];
}
function pl(e) {
	return e.split(/,(?=\s*[^;,\s]+=)/).map((e) => e.trim()).filter((e) => e.length > 0);
}
function ml(e) {
	let t = e.split(";", 1)[0], n = t.indexOf("=");
	if (n <= 0) return;
	let r = t.slice(0, n).trim();
	if (r) return {
		name: r,
		value: t.slice(n + 1).trim()
	};
}
function hl(e, t) {
	let n = /* @__PURE__ */ new Map();
	for (let t of gl(e)) n.set(t.name, t.value);
	for (let e of gl(t ?? void 0)) n.set(e.name, e.value);
	return n.size === 0 ? void 0 : Array.from(n).map(([e, t]) => `${e}=${t}`).join("; ");
}
function gl(e) {
	return e ? e.split(";").map(_l).filter((e) => e !== void 0) : [];
}
function _l(e) {
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
async function* vl(e) {
	let t = new TextDecoder(), n = e.getReader(), r = new qt(), i = [], a = (e) => {
		let n = t.decode(e);
		return n.endsWith("\r") ? n.slice(0, -1) : n;
	}, o = () => {
		if (i.length === 0) return;
		let e = i;
		return i = [], yl(e);
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
function yl(e) {
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
function bl(e, t = {}) {
	return new xl(e, t).stream;
}
var xl = class {
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
		this.serverUrl = e, this.fetchImpl = Sl(t.fetch), this.headers = t.headers ?? {}, this.cookiePolicy = t.cookies ?? "include", this.cookieStore = t.cookieStore ?? new dl(), this.ownsCookieStore = t.cookieStore === void 0, this.stream = {
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
			if (!ll(e)) throw Error("ACP HTTP stream first message must be initialize");
			let n = await this.fetchRequest({
				method: "POST",
				headers: { "Content-Type": al },
				body: JSON.stringify(e),
				signal: this.abortController.signal
			});
			if (!n.ok) throw await Cl("ACP initialize failed", n);
			let r = n.headers.get(nl);
			if (!r) throw Error("ACP initialize response missing Acp-Connection-Id");
			t = r, this.throwIfClosedDuringInitialize();
			let i = await n.json();
			if (this.throwIfClosedDuringInitialize(), !m(i)) throw Error("ACP initialize response was not a JSON-RPC response");
			if (ul(i.id) !== ("id" in e ? ul(e.id) : void 0)) throw Error("ACP initialize response id did not match initialize request");
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
		let r = n && "method" in e && "id" in e ? ul(e.id) : void 0;
		n && r && this.pendingSessionRequests.set(r, n);
		try {
			let r = await this.fetchRequest({
				method: "POST",
				headers: {
					"Content-Type": al,
					[nl]: t,
					...n ? { [rl]: n } : {}
				},
				body: JSON.stringify(e),
				signal: this.abortController.signal
			});
			if (!r.ok) throw await Cl("ACP POST failed", r);
			if (!("method" in e) && "id" in e) {
				let t = ul(e.id);
				t && this.pendingResponseSessions.delete(t);
			}
		} catch (e) {
			throw r && this.pendingSessionRequests.delete(r), this.errorReadable(e), e;
		}
	}
	sessionIdForOutboundMessage(e) {
		let t = sl(e);
		if (t) return t;
		if (!("id" in e) || "method" in e) return;
		let n = ul(e.id);
		return n ? this.pendingResponseSessions.get(n) : void 0;
	}
	openConnectionSse() {
		let e = this.connectionId;
		e && this.openSse({ [nl]: e });
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
			[nl]: n,
			[rl]: e
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
		let n = e[rl];
		try {
			let r = await this.fetchRequest({
				method: "GET",
				headers: {
					Accept: il,
					...e
				},
				signal: this.abortController.signal
			});
			if (!r.ok) throw await Cl("ACP SSE connection failed", r);
			if (!r.body) throw Error("ACP SSE response missing body");
			t.onOpen?.();
			for await (let t of vl(r.body)) {
				if (this.isClosed) return;
				if (Array.isArray(t)) throw TypeError("ACP HTTP transport does not support JSON-RPC batch messages");
				let n = cl(t);
				n && this.openSessionSse(n), this.trackServerRequestRoute(t, e[rl]), this.trackInboundResponse(t), this.enqueue(t);
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
		let n = ul(e.id);
		n && this.pendingResponseSessions.set(n, t);
	}
	trackInboundResponse(e) {
		if (!m(e)) return;
		let t = ul(e.id);
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
			headers: { [nl]: e }
		});
		if (!t.ok) throw await Cl("ACP DELETE failed", t);
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
function Sl(e) {
	if (e) return e;
	if (typeof globalThis.fetch == "function") return (e, t) => globalThis.fetch(e, t);
	throw Error("createHttpStream requires globalThis.fetch or options.fetch");
}
async function Cl(e, t) {
	let n = await t.text().catch(() => "");
	return Error(n ? `${e}: ${t.status} ${t.statusText}: ${n}` : `${e}: ${t.status} ${t.statusText}`);
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/ws-utils.js
function wl(e, t, n) {
	if (e.on) {
		let r = (...e) => {
			n(...El(t, e));
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
function Tl(e) {
	let t = Ol(e);
	if (typeof t == "string") return t;
}
function El(e, t) {
	return e !== "message" || typeof t[1] != "boolean" ? t : t[1] ? [void 0] : [Dl(t[0])];
}
function Dl(e) {
	if (typeof e == "string") return e;
	if (e instanceof ArrayBuffer || ArrayBuffer.isView(e)) return new TextDecoder().decode(e);
	if (Al(e)) return jl(e);
}
function Ol(e) {
	let [t] = e;
	return kl(t) ? t.data : t;
}
function kl(e) {
	return typeof e == "object" && !!e && "data" in e;
}
function Al(e) {
	return Array.isArray(e) && e.every(ArrayBuffer.isView);
}
function jl(e) {
	let t = e.reduce((e, t) => e + t.byteLength, 0), n = new Uint8Array(t), r = 0;
	for (let t of e) n.set(new Uint8Array(t.buffer, t.byteOffset, t.byteLength), r), r += t.byteLength;
	return new TextDecoder().decode(n);
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/ws-stream.js
var Ml = 1;
function Nl(e, t = {}) {
	return new Pl(e, t).stream;
}
var Pl = class {
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
		let n = zl(t.WebSocket), r = t.cookies ?? "include";
		this.cookieStore = t.cookieStore ?? new dl(), this.ownsCookieStore = t.cookieStore === void 0, this.socket = new n(e, t.protocols, { headers: Fl(t.headers, r, this.cookieStore) }), this.openPromise = new Promise((e, t) => {
			this.resolveOpen = e, this.rejectOpen = t;
		}), this.openPromise.catch(() => void 0), this.detachListeners.push(wl(this.socket, "open", () => {
			this.resolveOpen?.(), this.resolveOpen = void 0, this.rejectOpen = void 0, this.openPromise = void 0;
		})), this.detachListeners.push(wl(this.socket, "message", (...e) => {
			this.handleSocketMessage(e);
		})), this.detachListeners.push(wl(this.socket, "close", () => {
			this.closeReadable();
		})), this.detachListeners.push(wl(this.socket, "error", (e) => {
			this.errorReadable(e);
		})), r === "include" && this.detachListeners.push(wl(this.socket, "upgrade", (e) => {
			let t = Ll(e);
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
		this.socket.readyState !== void 0 && this.socket.readyState !== Ml && await this.openPromise;
	}
	handleSocketMessage(e) {
		if (this.isClosed) return;
		let t = Tl(e);
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
function Fl(e, t, n) {
	let r = e ? { ...e } : {};
	if (t === "include") {
		let t = new Headers(e);
		n.apply(t);
		let i = t.get("Cookie");
		i && (r[Il(r, "Cookie") ?? "Cookie"] = i);
	}
	return Object.keys(r).length > 0 ? r : void 0;
}
function Il(e, t) {
	return Object.keys(e).find((e) => e.toLowerCase() === t.toLowerCase());
}
function Ll(e) {
	if (e instanceof Headers) return e;
	if (!(!h(e) || !("headers" in e))) return Rl(e.headers);
}
function Rl(e) {
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
function zl(e) {
	if (e) return e;
	if (typeof globalThis.WebSocket == "function") return globalThis.WebSocket;
	throw Error("createWebSocketStream requires globalThis.WebSocket or options.WebSocket");
}
//#endregion
//#region src/core/transport.ts
function Bl(e, t = {}) {
	let n = Hl(e, t.fetch ?? globalThis.fetch), r = dn(t.maxMessageBytes);
	return {
		maxMessageBytes: r,
		open({ signal: i }) {
			return Ul(bl(e, {
				fetch: n,
				...t.headers ? { headers: { ...t.headers } } : {},
				...t.cookies ? { cookies: t.cookies } : {}
			}), i, r);
		}
	};
}
function Vl(e, t = {}) {
	let n = dn(t.maxMessageBytes);
	return {
		maxMessageBytes: n,
		open({ signal: r }) {
			return Ul(Nl(e, {
				protocols: [...t.protocols ?? []],
				...t.headers ? { headers: { ...t.headers } } : {},
				...t.cookies ? { cookies: t.cookies } : {},
				...t.WebSocket ? { WebSocket: t.WebSocket } : {}
			}), r, n);
		}
	};
}
function Hl(e, t) {
	if (!t) throw new u("INVALID_CONFIGURATION", "Streamable HTTP requires a fetch implementation", { phase: "transport/http" });
	let n = Wl(e);
	return async (e, r) => {
		let i = Gl(e, n);
		for (let a = 0; a <= 5; a += 1) {
			let o = await t(e, {
				...r,
				redirect: "manual"
			});
			if (o.type === "opaqueredirect") throw new u("INVALID_CONFIGURATION", "ACP HTTP redirects are opaque in browsers; configure a redirect-free endpoint", { phase: "transport/redirect" });
			if (!Kl(o.status)) return o;
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
function Ul(e, t, n) {
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
				if (!ln(i.value, n)) {
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
				if (!ln(e, n)) throw new u("PROTOCOL_VIOLATION", `ACP wire message exceeded the ${n} byte decoded output limit`, {
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
function Wl(e) {
	try {
		return new URL(e, globalThis.location === void 0 ? void 0 : globalThis.location.href);
	} catch (t) {
		throw new u("INVALID_CONFIGURATION", `ACP HTTP endpoint must be an absolute URL: ${e}`, {
			cause: t,
			phase: "transport/http"
		});
	}
}
function Gl(e, t) {
	return typeof e == "string" ? new URL(e, t) : e instanceof URL ? e : new URL(e.url, t);
}
function Kl(e) {
	return e >= 300 && e <= 399;
}
//#endregion
//#region src/standalone.tsx
var ql = 256, Jl = /^[A-Za-z0-9+/_-]+={0,2}$/, Yl = /* @__PURE__ */ new WeakMap(), Xl = /* @__PURE__ */ new WeakMap();
function Zl(e, t) {
	if (Yl.has(e)) throw Error("pretty-aui: this target is already mounted");
	let n = Object.hasOwn(t, "options");
	if (n === Object.hasOwn(t, "controller")) throw TypeError("pretty-aui: mountChat requires exactly one of options or controller");
	t.styleNonce !== void 0 && Ql(t.styleNonce);
	let r = Xl.get(e);
	if (e.shadowRoot && e.shadowRoot !== r) throw Error("pretty-aui: mountChat requires a target without an existing shadow root");
	let i = r ?? e.attachShadow({ mode: "open" });
	Xl.set(e, i);
	let a = document.createElement("style");
	t.styleNonce !== void 0 && (a.nonce = t.styleNonce), a.textContent = tl;
	let o = document.createElement("div");
	o.className = "pretty-aui-standalone-root", i.append(a, o);
	let s = {
		shadow: i,
		style: a,
		container: o
	};
	Yl.set(e, s);
	let { surface: c, colorScheme: l, labels: u } = t, d = n ? gn(t.options) : t.controller, f = It(o);
	f.render(/* @__PURE__ */ W(gs, {
		sessionOrganization: t.sessionOrganization,
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
					Yl.get(e) === s && (a.remove(), o.remove(), Yl.delete(e));
				}
			}
		}
	};
	return typeof MutationObserver < "u" && (m = tu(e, () => void h())), {
		controller: d,
		ready: d.ready,
		setDraft(e, t) {
			$l(p), d.setDraft(e), t?.focus && eu(i).focus();
		},
		focusComposer() {
			$l(p), eu(i).focus();
		},
		unmount: h
	};
}
function Ql(e) {
	if (e.length === 0 || e.length > ql || !Jl.test(e)) throw TypeError("pretty-aui: styleNonce is not a valid CSP nonce");
}
function $l(e) {
	if (e) throw Error("pretty-aui: mount has been unmounted");
}
function eu(e) {
	let t = e.querySelector("[data-pretty-aui-slot=\"composer-input\"] textarea");
	if (!t) throw Error("pretty-aui: composer is not mounted yet");
	return t;
}
function tu(e, t) {
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
export { u as PrettyAuiError, gn as createChat, Bl as createStreamableHttpConnector, Vl as createWebSocketConnector, Zl as mountChat };

//# sourceMappingURL=pretty-aui.js.map