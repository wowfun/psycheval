globalThis.__zod_globalConfig ??= {}, globalThis.__zod_globalConfig.jitless = !0;
//#region src/core/errors.ts
var e = class extends Error {
	code;
	protocol;
	phase;
	retryable;
	accepted;
	completionUnknown;
	constructor(e, t, n = {}) {
		super(t, { cause: n.cause }), this.name = "PrettyAuiError", this.code = e, this.phase = n.phase ?? "unknown", this.retryable = n.retryable ?? !1, n.protocol !== void 0 && (this.protocol = n.protocol), n.accepted !== void 0 && (this.accepted = n.accepted), n.completionUnknown !== void 0 && (this.completionUnknown = n.completionUnknown);
	}
};
function t(t) {
	return t instanceof e ? {
		code: t.code,
		message: t.message,
		retryable: t.retryable,
		...t.accepted === void 0 ? {} : { accepted: t.accepted },
		...t.completionUnknown === void 0 ? {} : { completionUnknown: t.completionUnknown }
	} : {
		code: "UNKNOWN",
		message: t instanceof Error ? t.message : String(t),
		retryable: !1
	};
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/schema/index.js
var n = {
	initialize: "initialize",
	authenticate: "authenticate",
	providers_list: "providers/list",
	providers_set: "providers/set",
	providers_disable: "providers/disable",
	session_new: "session/new",
	session_load: "session/load",
	session_set_mode: "session/set_mode",
	session_set_config_option: "session/set_config_option",
	session_prompt: "session/prompt",
	session_cancel: "session/cancel",
	mcp_message: "mcp/message",
	session_list: "session/list",
	session_delete: "session/delete",
	session_fork: "session/fork",
	session_resume: "session/resume",
	session_close: "session/close",
	logout: "logout",
	nes_start: "nes/start",
	nes_suggest: "nes/suggest",
	nes_accept: "nes/accept",
	nes_reject: "nes/reject",
	nes_close: "nes/close",
	document_did_open: "document/didOpen",
	document_did_change: "document/didChange",
	document_did_close: "document/didClose",
	document_did_save: "document/didSave",
	document_did_focus: "document/didFocus"
}, r = {
	session_request_permission: "session/request_permission",
	session_update: "session/update",
	fs_write_text_file: "fs/write_text_file",
	fs_read_text_file: "fs/read_text_file",
	terminal_create: "terminal/create",
	terminal_output: "terminal/output",
	terminal_release: "terminal/release",
	terminal_wait_for_exit: "terminal/wait_for_exit",
	terminal_kill: "terminal/kill",
	mcp_connect: "mcp/connect",
	mcp_message: "mcp/message",
	mcp_disconnect: "mcp/disconnect",
	elicitation_create: "elicitation/create",
	elicitation_complete: "elicitation/complete"
}, i = { cancel_request: "$/cancel_request" }, a, o = /*@__PURE__*/ Object.freeze({ status: "aborted" });
function s(e, t, n) {
	function r(n, r) {
		if (n._zod || Object.defineProperty(n, "_zod", {
			value: {
				def: r,
				constr: o,
				traits: /* @__PURE__ */ new Set()
			},
			enumerable: !1
		}), n._zod.traits.has(e)) return;
		n._zod.traits.add(e), t(n, r);
		let i = o.prototype, a = Object.keys(i);
		for (let e = 0; e < a.length; e++) {
			let t = a[e];
			t in n || (n[t] = i[t].bind(n));
		}
	}
	let i = n?.Parent ?? Object;
	class a extends i {}
	Object.defineProperty(a, "name", { value: e });
	function o(e) {
		var t;
		let i = n?.Parent ? new a() : this;
		r(i, e), (t = i._zod).deferred ?? (t.deferred = []);
		for (let e of i._zod.deferred) e();
		return i;
	}
	return Object.defineProperty(o, "init", { value: r }), Object.defineProperty(o, Symbol.hasInstance, { value: (t) => n?.Parent && t instanceof n.Parent ? !0 : t?._zod?.traits?.has(e) }), Object.defineProperty(o, "name", { value: e }), o;
}
var c = class extends Error {
	constructor() {
		super("Encountered Promise during synchronous parse. Use .parseAsync() instead.");
	}
}, l = class extends Error {
	constructor(e) {
		super(`Encountered unidirectional transform during encode: ${e}`), this.name = "ZodEncodeError";
	}
};
(a = globalThis).__zod_globalConfig ?? (a.__zod_globalConfig = {});
var u = globalThis.__zod_globalConfig;
function d(e) {
	return e && Object.assign(u, e), u;
}
//#endregion
//#region node_modules/.pnpm/zod@4.4.3/node_modules/zod/v4/core/util.js
function f(e) {
	let t = Object.values(e).filter((e) => typeof e == "number");
	return Object.entries(e).filter(([e, n]) => t.indexOf(+e) === -1).map(([e, t]) => t);
}
function p(e, t) {
	return typeof t == "bigint" ? t.toString() : t;
}
function ee(e) {
	return { get value() {
		{
			let t = e();
			return Object.defineProperty(this, "value", { value: t }), t;
		}
	} };
}
function te(e) {
	return e == null;
}
function ne(e) {
	let t = +!!e.startsWith("^"), n = e.endsWith("$") ? e.length - 1 : e.length;
	return e.slice(t, n);
}
function re(e, t) {
	let n = e / t, r = Math.round(n), i = 2 ** -52 * Math.max(Math.abs(n), 1);
	return Math.abs(n - r) < i ? 0 : n - r;
}
var ie = /* @__PURE__*/ Symbol("evaluating");
function m(e, t, n) {
	let r;
	Object.defineProperty(e, t, {
		get() {
			if (r !== ie) return r === void 0 && (r = ie, r = n()), r;
		},
		set(n) {
			Object.defineProperty(e, t, { value: n });
		},
		configurable: !0
	});
}
function h(e, t, n) {
	Object.defineProperty(e, t, {
		value: n,
		writable: !0,
		enumerable: !0,
		configurable: !0
	});
}
function g(...e) {
	let t = {};
	for (let n of e) {
		let e = Object.getOwnPropertyDescriptors(n);
		Object.assign(t, e);
	}
	return Object.defineProperties({}, t);
}
function ae(e) {
	return JSON.stringify(e);
}
function oe(e) {
	return e.toLowerCase().trim().replace(/[^\w\s-]/g, "").replace(/[\s_-]+/g, "-").replace(/^-+|-+$/g, "");
}
var se = "captureStackTrace" in Error ? Error.captureStackTrace : (...e) => {};
function ce(e) {
	return typeof e == "object" && !!e && !Array.isArray(e);
}
var le = /* @__PURE__*/ ee(() => {
	if (u.jitless || typeof navigator < "u" && navigator?.userAgent?.includes("Cloudflare")) return !1;
	try {
		return Function(""), !0;
	} catch {
		return !1;
	}
});
function ue(e) {
	if (ce(e) === !1) return !1;
	let t = e.constructor;
	if (t === void 0 || typeof t != "function") return !0;
	let n = t.prototype;
	return ce(n) !== !1 && Object.prototype.hasOwnProperty.call(n, "isPrototypeOf") !== !1;
}
function de(e) {
	return ue(e) ? { ...e } : Array.isArray(e) ? [...e] : e instanceof Map ? new Map(e) : e instanceof Set ? new Set(e) : e;
}
var fe = /* @__PURE__*/ new Set([
	"string",
	"number",
	"symbol"
]);
function pe(e) {
	return e.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
function _(e, t, n) {
	let r = new e._zod.constr(t ?? e._zod.def);
	return (!t || n?.parent) && (r._zod.parent = e), r;
}
function v(e) {
	let t = e;
	if (!t) return {};
	if (typeof t == "string") return { error: () => t };
	if (t?.message !== void 0) {
		if (t?.error !== void 0) throw Error("Cannot specify both `message` and `error` params");
		t.error = t.message;
	}
	return delete t.message, typeof t.error == "string" ? {
		...t,
		error: () => t.error
	} : t;
}
function me(e) {
	return Object.keys(e).filter((t) => e[t]._zod.optin === "optional" && e[t]._zod.optout === "optional");
}
var he = {
	safeint: [-(2 ** 53 - 1), 2 ** 53 - 1],
	int32: [-2147483648, 2147483647],
	uint32: [0, 4294967295],
	float32: [-34028234663852886e22, 34028234663852886e22],
	float64: [-Number.MAX_VALUE, Number.MAX_VALUE]
};
function ge(e, t) {
	let n = e._zod.def, r = n.checks;
	if (r && r.length > 0) throw Error(".pick() cannot be used on object schemas containing refinements");
	return _(e, g(e._zod.def, {
		get shape() {
			let e = {};
			for (let r in t) {
				if (!(r in n.shape)) throw Error(`Unrecognized key: "${r}"`);
				t[r] && (e[r] = n.shape[r]);
			}
			return h(this, "shape", e), e;
		},
		checks: []
	}));
}
function _e(e, t) {
	let n = e._zod.def, r = n.checks;
	if (r && r.length > 0) throw Error(".omit() cannot be used on object schemas containing refinements");
	return _(e, g(e._zod.def, {
		get shape() {
			let r = { ...e._zod.def.shape };
			for (let e in t) {
				if (!(e in n.shape)) throw Error(`Unrecognized key: "${e}"`);
				t[e] && delete r[e];
			}
			return h(this, "shape", r), r;
		},
		checks: []
	}));
}
function ve(e, t) {
	if (!ue(t)) throw Error("Invalid input to extend: expected a plain object");
	let n = e._zod.def.checks;
	if (n && n.length > 0) {
		let n = e._zod.def.shape;
		for (let e in t) if (Object.getOwnPropertyDescriptor(n, e) !== void 0) throw Error("Cannot overwrite keys on object schemas containing refinements. Use `.safeExtend()` instead.");
	}
	return _(e, g(e._zod.def, { get shape() {
		let n = {
			...e._zod.def.shape,
			...t
		};
		return h(this, "shape", n), n;
	} }));
}
function ye(e, t) {
	if (!ue(t)) throw Error("Invalid input to safeExtend: expected a plain object");
	return _(e, g(e._zod.def, { get shape() {
		let n = {
			...e._zod.def.shape,
			...t
		};
		return h(this, "shape", n), n;
	} }));
}
function be(e, t) {
	if (e._zod.def.checks?.length) throw Error(".merge() cannot be used on object schemas containing refinements. Use .safeExtend() instead.");
	return _(e, g(e._zod.def, {
		get shape() {
			let n = {
				...e._zod.def.shape,
				...t._zod.def.shape
			};
			return h(this, "shape", n), n;
		},
		get catchall() {
			return t._zod.def.catchall;
		},
		checks: t._zod.def.checks ?? []
	}));
}
function xe(e, t, n) {
	let r = t._zod.def.checks;
	if (r && r.length > 0) throw Error(".partial() cannot be used on object schemas containing refinements");
	return _(t, g(t._zod.def, {
		get shape() {
			let r = t._zod.def.shape, i = { ...r };
			if (n) for (let t in n) {
				if (!(t in r)) throw Error(`Unrecognized key: "${t}"`);
				n[t] && (i[t] = e ? new e({
					type: "optional",
					innerType: r[t]
				}) : r[t]);
			}
			else for (let t in r) i[t] = e ? new e({
				type: "optional",
				innerType: r[t]
			}) : r[t];
			return h(this, "shape", i), i;
		},
		checks: []
	}));
}
function Se(e, t, n) {
	return _(t, g(t._zod.def, { get shape() {
		let r = t._zod.def.shape, i = { ...r };
		if (n) for (let t in n) {
			if (!(t in i)) throw Error(`Unrecognized key: "${t}"`);
			n[t] && (i[t] = new e({
				type: "nonoptional",
				innerType: r[t]
			}));
		}
		else for (let t in r) i[t] = new e({
			type: "nonoptional",
			innerType: r[t]
		});
		return h(this, "shape", i), i;
	} }));
}
function Ce(e, t = 0) {
	if (e.aborted === !0) return !0;
	for (let n = t; n < e.issues.length; n++) if (e.issues[n]?.continue !== !0) return !0;
	return !1;
}
function we(e, t = 0) {
	if (e.aborted === !0) return !0;
	for (let n = t; n < e.issues.length; n++) if (e.issues[n]?.continue === !1) return !0;
	return !1;
}
function Te(e, t) {
	return t.map((t) => {
		var n;
		return (n = t).path ?? (n.path = []), t.path.unshift(e), t;
	});
}
function Ee(e) {
	return typeof e == "string" ? e : e?.message;
}
function y(e, t, n) {
	let r = e.message ? e.message : Ee(e.inst?._zod.def?.error?.(e)) ?? Ee(t?.error?.(e)) ?? Ee(n.customError?.(e)) ?? Ee(n.localeError?.(e)) ?? "Invalid input", { inst: i, continue: a, input: o, ...s } = e;
	return s.path ??= [], s.message = r, t?.reportInput && (s.input = o), s;
}
function De(e) {
	return Array.isArray(e) ? "array" : typeof e == "string" ? "string" : "unknown";
}
function Oe(...e) {
	let [t, n, r] = e;
	return typeof t == "string" ? {
		message: t,
		code: "custom",
		input: n,
		inst: r
	} : { ...t };
}
//#endregion
//#region node_modules/.pnpm/zod@4.4.3/node_modules/zod/v4/core/errors.js
var ke = (e, t) => {
	e.name = "$ZodError", Object.defineProperty(e, "_zod", {
		value: e._zod,
		enumerable: !1
	}), Object.defineProperty(e, "issues", {
		value: t,
		enumerable: !1
	}), e.message = JSON.stringify(t, p, 2), Object.defineProperty(e, "toString", {
		value: () => e.message,
		enumerable: !1
	});
}, Ae = s("$ZodError", ke), je = s("$ZodError", ke, { Parent: Error });
function Me(e, t = (e) => e.message) {
	let n = {}, r = [];
	for (let i of e.issues) i.path.length > 0 ? (n[i.path[0]] = n[i.path[0]] || [], n[i.path[0]].push(t(i))) : r.push(t(i));
	return {
		formErrors: r,
		fieldErrors: n
	};
}
function Ne(e, t = (e) => e.message) {
	let n = { _errors: [] }, r = (e, i = []) => {
		for (let a of e.issues) if (a.code === "invalid_union" && a.errors.length) a.errors.map((e) => r({ issues: e }, [...i, ...a.path]));
		else if (a.code === "invalid_key") r({ issues: a.issues }, [...i, ...a.path]);
		else if (a.code === "invalid_element") r({ issues: a.issues }, [...i, ...a.path]);
		else {
			let e = [...i, ...a.path];
			if (e.length === 0) n._errors.push(t(a));
			else {
				let r = n, i = 0;
				for (; i < e.length;) {
					let n = e[i];
					i === e.length - 1 ? (r[n] = r[n] || { _errors: [] }, r[n]._errors.push(t(a))) : r[n] = r[n] || { _errors: [] }, r = r[n], i++;
				}
			}
		}
	};
	return r(e), n;
}
//#endregion
//#region node_modules/.pnpm/zod@4.4.3/node_modules/zod/v4/core/parse.js
var Pe = (e) => (t, n, r, i) => {
	let a = r ? {
		...r,
		async: !1
	} : { async: !1 }, o = t._zod.run({
		value: n,
		issues: []
	}, a);
	if (o instanceof Promise) throw new c();
	if (o.issues.length) {
		let t = new ((i?.Err) ?? e)(o.issues.map((e) => y(e, a, d())));
		throw se(t, i?.callee), t;
	}
	return o.value;
}, Fe = (e) => async (t, n, r, i) => {
	let a = r ? {
		...r,
		async: !0
	} : { async: !0 }, o = t._zod.run({
		value: n,
		issues: []
	}, a);
	if (o instanceof Promise && (o = await o), o.issues.length) {
		let t = new ((i?.Err) ?? e)(o.issues.map((e) => y(e, a, d())));
		throw se(t, i?.callee), t;
	}
	return o.value;
}, Ie = (e) => (t, n, r) => {
	let i = r ? {
		...r,
		async: !1
	} : { async: !1 }, a = t._zod.run({
		value: n,
		issues: []
	}, i);
	if (a instanceof Promise) throw new c();
	return a.issues.length ? {
		success: !1,
		error: new (e ?? Ae)(a.issues.map((e) => y(e, i, d())))
	} : {
		success: !0,
		data: a.value
	};
}, Le = /* @__PURE__*/ Ie(je), Re = (e) => async (t, n, r) => {
	let i = r ? {
		...r,
		async: !0
	} : { async: !0 }, a = t._zod.run({
		value: n,
		issues: []
	}, i);
	return a instanceof Promise && (a = await a), a.issues.length ? {
		success: !1,
		error: new e(a.issues.map((e) => y(e, i, d())))
	} : {
		success: !0,
		data: a.value
	};
}, ze = /* @__PURE__*/ Re(je), Be = (e) => (t, n, r) => {
	let i = r ? {
		...r,
		direction: "backward"
	} : { direction: "backward" };
	return Pe(e)(t, n, i);
}, Ve = (e) => (t, n, r) => Pe(e)(t, n, r), He = (e) => async (t, n, r) => {
	let i = r ? {
		...r,
		direction: "backward"
	} : { direction: "backward" };
	return Fe(e)(t, n, i);
}, Ue = (e) => async (t, n, r) => Fe(e)(t, n, r), We = (e) => (t, n, r) => {
	let i = r ? {
		...r,
		direction: "backward"
	} : { direction: "backward" };
	return Ie(e)(t, n, i);
}, Ge = (e) => (t, n, r) => Ie(e)(t, n, r), Ke = (e) => async (t, n, r) => {
	let i = r ? {
		...r,
		direction: "backward"
	} : { direction: "backward" };
	return Re(e)(t, n, i);
}, qe = (e) => async (t, n, r) => Re(e)(t, n, r), Je = /^[cC][0-9a-z]{6,}$/, Ye = /^[0-9a-z]+$/, Xe = /^[0-9A-HJKMNP-TV-Za-hjkmnp-tv-z]{26}$/, Ze = /^[0-9a-vA-V]{20}$/, Qe = /^[A-Za-z0-9]{27}$/, $e = /^[a-zA-Z0-9_-]{21}$/, et = /^P(?:(\d+W)|(?!.*W)(?=\d|T\d)(\d+Y)?(\d+M)?(\d+D)?(T(?=\d)(\d+H)?(\d+M)?(\d+([.,]\d+)?S)?)?)$/, tt = /^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$/, nt = (e) => e ? RegExp(`^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-${e}[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12})$`) : /^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$/, rt = /^(?!\.)(?!.*\.\.)([A-Za-z0-9_'+\-\.]*)[A-Za-z0-9_+-]@([A-Za-z0-9][A-Za-z0-9\-]*\.)+[A-Za-z]{2,}$/, it = "^(\\p{Extended_Pictographic}|\\p{Emoji_Component})+$";
function at() {
	return new RegExp(it, "u");
}
var ot = /^(?:(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])\.){3}(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])$/, st = /^(([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:))$/, ct = /^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])\/([0-9]|[1-2][0-9]|3[0-2])$/, lt = /^(([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|::|([0-9a-fA-F]{1,4})?::([0-9a-fA-F]{1,4}:?){0,6})\/(12[0-8]|1[01][0-9]|[1-9]?[0-9])$/, ut = /^$|^(?:[0-9a-zA-Z+/]{4})*(?:(?:[0-9a-zA-Z+/]{2}==)|(?:[0-9a-zA-Z+/]{3}=))?$/, dt = /^[A-Za-z0-9_-]*$/, ft = /^https?$/, pt = /^\+[1-9]\d{6,14}$/, mt = "(?:(?:\\d\\d[2468][048]|\\d\\d[13579][26]|\\d\\d0[48]|[02468][048]00|[13579][26]00)-02-29|\\d{4}-(?:(?:0[13578]|1[02])-(?:0[1-9]|[12]\\d|3[01])|(?:0[469]|11)-(?:0[1-9]|[12]\\d|30)|(?:02)-(?:0[1-9]|1\\d|2[0-8])))", ht = /*@__PURE__*/ RegExp(`^${mt}$`);
function gt(e) {
	let t = "(?:[01]\\d|2[0-3]):[0-5]\\d";
	return typeof e.precision == "number" ? e.precision === -1 ? `${t}` : e.precision === 0 ? `${t}:[0-5]\\d` : `${t}:[0-5]\\d\\.\\d{${e.precision}}` : `${t}(?::[0-5]\\d(?:\\.\\d+)?)?`;
}
function _t(e) {
	return RegExp(`^${gt(e)}$`);
}
function vt(e) {
	let t = gt({ precision: e.precision }), n = ["Z"];
	e.local && n.push(""), e.offset && n.push("([+-](?:[01]\\d|2[0-3]):[0-5]\\d)");
	let r = `${t}(?:${n.join("|")})`;
	return RegExp(`^${mt}T(?:${r})$`);
}
var yt = (e) => {
	let t = e ? `[\\s\\S]{${e?.minimum ?? 0},${e?.maximum ?? ""}}` : "[\\s\\S]*";
	return RegExp(`^${t}$`);
}, bt = /^-?\d+$/, xt = /^-?\d+(?:\.\d+)?$/, St = /^(?:true|false)$/i, Ct = /^[^A-Z]*$/, wt = /^[^a-z]*$/, b = /*@__PURE__*/ s("$ZodCheck", (e, t) => {
	var n;
	e._zod ??= {}, e._zod.def = t, (n = e._zod).onattach ?? (n.onattach = []);
}), Tt = {
	number: "number",
	bigint: "bigint",
	object: "date"
}, Et = /*@__PURE__*/ s("$ZodCheckLessThan", (e, t) => {
	b.init(e, t);
	let n = Tt[typeof t.value];
	e._zod.onattach.push((e) => {
		let n = e._zod.bag, r = (t.inclusive ? n.maximum : n.exclusiveMaximum) ?? Infinity;
		t.value < r && (t.inclusive ? n.maximum = t.value : n.exclusiveMaximum = t.value);
	}), e._zod.check = (r) => {
		(t.inclusive ? r.value <= t.value : r.value < t.value) || r.issues.push({
			origin: n,
			code: "too_big",
			maximum: typeof t.value == "object" ? t.value.getTime() : t.value,
			input: r.value,
			inclusive: t.inclusive,
			inst: e,
			continue: !t.abort
		});
	};
}), Dt = /*@__PURE__*/ s("$ZodCheckGreaterThan", (e, t) => {
	b.init(e, t);
	let n = Tt[typeof t.value];
	e._zod.onattach.push((e) => {
		let n = e._zod.bag, r = (t.inclusive ? n.minimum : n.exclusiveMinimum) ?? -Infinity;
		t.value > r && (t.inclusive ? n.minimum = t.value : n.exclusiveMinimum = t.value);
	}), e._zod.check = (r) => {
		(t.inclusive ? r.value >= t.value : r.value > t.value) || r.issues.push({
			origin: n,
			code: "too_small",
			minimum: typeof t.value == "object" ? t.value.getTime() : t.value,
			input: r.value,
			inclusive: t.inclusive,
			inst: e,
			continue: !t.abort
		});
	};
}), Ot = /*@__PURE__*/ s("$ZodCheckMultipleOf", (e, t) => {
	b.init(e, t), e._zod.onattach.push((e) => {
		var n;
		(n = e._zod.bag).multipleOf ?? (n.multipleOf = t.value);
	}), e._zod.check = (n) => {
		if (typeof n.value != typeof t.value) throw Error("Cannot mix number and bigint in multiple_of check.");
		(typeof n.value == "bigint" ? n.value % t.value === BigInt(0) : re(n.value, t.value) === 0) || n.issues.push({
			origin: typeof n.value,
			code: "not_multiple_of",
			divisor: t.value,
			input: n.value,
			inst: e,
			continue: !t.abort
		});
	};
}), kt = /*@__PURE__*/ s("$ZodCheckNumberFormat", (e, t) => {
	b.init(e, t), t.format = t.format || "float64";
	let n = t.format?.includes("int"), r = n ? "int" : "number", [i, a] = he[t.format];
	e._zod.onattach.push((e) => {
		let r = e._zod.bag;
		r.format = t.format, r.minimum = i, r.maximum = a, n && (r.pattern = bt);
	}), e._zod.check = (o) => {
		let s = o.value;
		if (n) {
			if (!Number.isInteger(s)) {
				o.issues.push({
					expected: r,
					format: t.format,
					code: "invalid_type",
					continue: !1,
					input: s,
					inst: e
				});
				return;
			}
			if (!Number.isSafeInteger(s)) {
				s > 0 ? o.issues.push({
					input: s,
					code: "too_big",
					maximum: 2 ** 53 - 1,
					note: "Integers must be within the safe integer range.",
					inst: e,
					origin: r,
					inclusive: !0,
					continue: !t.abort
				}) : o.issues.push({
					input: s,
					code: "too_small",
					minimum: -(2 ** 53 - 1),
					note: "Integers must be within the safe integer range.",
					inst: e,
					origin: r,
					inclusive: !0,
					continue: !t.abort
				});
				return;
			}
		}
		s < i && o.issues.push({
			origin: "number",
			input: s,
			code: "too_small",
			minimum: i,
			inclusive: !0,
			inst: e,
			continue: !t.abort
		}), s > a && o.issues.push({
			origin: "number",
			input: s,
			code: "too_big",
			maximum: a,
			inclusive: !0,
			inst: e,
			continue: !t.abort
		});
	};
}), At = /*@__PURE__*/ s("$ZodCheckMaxLength", (e, t) => {
	var n;
	b.init(e, t), (n = e._zod.def).when ?? (n.when = (e) => {
		let t = e.value;
		return !te(t) && t.length !== void 0;
	}), e._zod.onattach.push((e) => {
		let n = e._zod.bag.maximum ?? Infinity;
		t.maximum < n && (e._zod.bag.maximum = t.maximum);
	}), e._zod.check = (n) => {
		let r = n.value;
		if (r.length <= t.maximum) return;
		let i = De(r);
		n.issues.push({
			origin: i,
			code: "too_big",
			maximum: t.maximum,
			inclusive: !0,
			input: r,
			inst: e,
			continue: !t.abort
		});
	};
}), jt = /*@__PURE__*/ s("$ZodCheckMinLength", (e, t) => {
	var n;
	b.init(e, t), (n = e._zod.def).when ?? (n.when = (e) => {
		let t = e.value;
		return !te(t) && t.length !== void 0;
	}), e._zod.onattach.push((e) => {
		let n = e._zod.bag.minimum ?? -Infinity;
		t.minimum > n && (e._zod.bag.minimum = t.minimum);
	}), e._zod.check = (n) => {
		let r = n.value;
		if (r.length >= t.minimum) return;
		let i = De(r);
		n.issues.push({
			origin: i,
			code: "too_small",
			minimum: t.minimum,
			inclusive: !0,
			input: r,
			inst: e,
			continue: !t.abort
		});
	};
}), Mt = /*@__PURE__*/ s("$ZodCheckLengthEquals", (e, t) => {
	var n;
	b.init(e, t), (n = e._zod.def).when ?? (n.when = (e) => {
		let t = e.value;
		return !te(t) && t.length !== void 0;
	}), e._zod.onattach.push((e) => {
		let n = e._zod.bag;
		n.minimum = t.length, n.maximum = t.length, n.length = t.length;
	}), e._zod.check = (n) => {
		let r = n.value, i = r.length;
		if (i === t.length) return;
		let a = De(r), o = i > t.length;
		n.issues.push({
			origin: a,
			...o ? {
				code: "too_big",
				maximum: t.length
			} : {
				code: "too_small",
				minimum: t.length
			},
			inclusive: !0,
			exact: !0,
			input: n.value,
			inst: e,
			continue: !t.abort
		});
	};
}), Nt = /*@__PURE__*/ s("$ZodCheckStringFormat", (e, t) => {
	var n, r;
	b.init(e, t), e._zod.onattach.push((e) => {
		let n = e._zod.bag;
		n.format = t.format, t.pattern && (n.patterns ??= /* @__PURE__ */ new Set(), n.patterns.add(t.pattern));
	}), t.pattern ? (n = e._zod).check ?? (n.check = (n) => {
		t.pattern.lastIndex = 0, !t.pattern.test(n.value) && n.issues.push({
			origin: "string",
			code: "invalid_format",
			format: t.format,
			input: n.value,
			...t.pattern ? { pattern: t.pattern.toString() } : {},
			inst: e,
			continue: !t.abort
		});
	}) : (r = e._zod).check ?? (r.check = () => {});
}), Pt = /*@__PURE__*/ s("$ZodCheckRegex", (e, t) => {
	Nt.init(e, t), e._zod.check = (n) => {
		t.pattern.lastIndex = 0, !t.pattern.test(n.value) && n.issues.push({
			origin: "string",
			code: "invalid_format",
			format: "regex",
			input: n.value,
			pattern: t.pattern.toString(),
			inst: e,
			continue: !t.abort
		});
	};
}), Ft = /*@__PURE__*/ s("$ZodCheckLowerCase", (e, t) => {
	t.pattern ??= Ct, Nt.init(e, t);
}), It = /*@__PURE__*/ s("$ZodCheckUpperCase", (e, t) => {
	t.pattern ??= wt, Nt.init(e, t);
}), Lt = /*@__PURE__*/ s("$ZodCheckIncludes", (e, t) => {
	b.init(e, t);
	let n = pe(t.includes), r = new RegExp(typeof t.position == "number" ? `^.{${t.position}}${n}` : n);
	t.pattern = r, e._zod.onattach.push((e) => {
		let t = e._zod.bag;
		t.patterns ??= /* @__PURE__ */ new Set(), t.patterns.add(r);
	}), e._zod.check = (n) => {
		n.value.includes(t.includes, t.position) || n.issues.push({
			origin: "string",
			code: "invalid_format",
			format: "includes",
			includes: t.includes,
			input: n.value,
			inst: e,
			continue: !t.abort
		});
	};
}), Rt = /*@__PURE__*/ s("$ZodCheckStartsWith", (e, t) => {
	b.init(e, t);
	let n = RegExp(`^${pe(t.prefix)}.*`);
	t.pattern ??= n, e._zod.onattach.push((e) => {
		let t = e._zod.bag;
		t.patterns ??= /* @__PURE__ */ new Set(), t.patterns.add(n);
	}), e._zod.check = (n) => {
		n.value.startsWith(t.prefix) || n.issues.push({
			origin: "string",
			code: "invalid_format",
			format: "starts_with",
			prefix: t.prefix,
			input: n.value,
			inst: e,
			continue: !t.abort
		});
	};
}), zt = /*@__PURE__*/ s("$ZodCheckEndsWith", (e, t) => {
	b.init(e, t);
	let n = RegExp(`.*${pe(t.suffix)}$`);
	t.pattern ??= n, e._zod.onattach.push((e) => {
		let t = e._zod.bag;
		t.patterns ??= /* @__PURE__ */ new Set(), t.patterns.add(n);
	}), e._zod.check = (n) => {
		n.value.endsWith(t.suffix) || n.issues.push({
			origin: "string",
			code: "invalid_format",
			format: "ends_with",
			suffix: t.suffix,
			input: n.value,
			inst: e,
			continue: !t.abort
		});
	};
}), Bt = /*@__PURE__*/ s("$ZodCheckOverwrite", (e, t) => {
	b.init(e, t), e._zod.check = (e) => {
		e.value = t.tx(e.value);
	};
}), Vt = class {
	constructor(e = []) {
		this.content = [], this.indent = 0, this && (this.args = e);
	}
	indented(e) {
		this.indent += 1, e(this), --this.indent;
	}
	write(e) {
		if (typeof e == "function") {
			e(this, { execution: "sync" }), e(this, { execution: "async" });
			return;
		}
		let t = e.split("\n").filter((e) => e), n = Math.min(...t.map((e) => e.length - e.trimStart().length)), r = t.map((e) => e.slice(n)).map((e) => " ".repeat(this.indent * 2) + e);
		for (let e of r) this.content.push(e);
	}
	compile() {
		let e = Function, t = this?.args, n = [...(this?.content ?? [""]).map((e) => `  ${e}`)];
		return new e(...t, n.join("\n"));
	}
}, Ht = {
	major: 4,
	minor: 4,
	patch: 3
}, x = /*@__PURE__*/ s("$ZodType", (e, t) => {
	var n;
	e ??= {}, e._zod.def = t, e._zod.bag = e._zod.bag || {}, e._zod.version = Ht;
	let r = [...e._zod.def.checks ?? []];
	e._zod.traits.has("$ZodCheck") && r.unshift(e);
	for (let t of r) for (let n of t._zod.onattach) n(e);
	if (r.length === 0) (n = e._zod).deferred ?? (n.deferred = []), e._zod.deferred?.push(() => {
		e._zod.run = e._zod.parse;
	});
	else {
		let t = (e, t, n) => {
			let r = Ce(e), i;
			for (let a of t) {
				if (a._zod.def.when) {
					if (we(e) || !a._zod.def.when(e)) continue;
				} else if (r) continue;
				let t = e.issues.length, o = a._zod.check(e);
				if (o instanceof Promise && n?.async === !1) throw new c();
				if (i || o instanceof Promise) i = (i ?? Promise.resolve()).then(async () => {
					await o, e.issues.length !== t && (r ||= Ce(e, t));
				});
				else {
					if (e.issues.length === t) continue;
					r ||= Ce(e, t);
				}
			}
			return i ? i.then(() => e) : e;
		}, n = (n, i, a) => {
			if (Ce(n)) return n.aborted = !0, n;
			let o = t(i, r, a);
			if (o instanceof Promise) {
				if (a.async === !1) throw new c();
				return o.then((t) => e._zod.parse(t, a));
			}
			return e._zod.parse(o, a);
		};
		e._zod.run = (i, a) => {
			if (a.skipChecks) return e._zod.parse(i, a);
			if (a.direction === "backward") {
				let t = e._zod.parse({
					value: i.value,
					issues: []
				}, {
					...a,
					skipChecks: !0
				});
				return t instanceof Promise ? t.then((e) => n(e, i, a)) : n(t, i, a);
			}
			let o = e._zod.parse(i, a);
			if (o instanceof Promise) {
				if (a.async === !1) throw new c();
				return o.then((e) => t(e, r, a));
			}
			return t(o, r, a);
		};
	}
	m(e, "~standard", () => ({
		validate: (t) => {
			try {
				let n = Le(e, t);
				return n.success ? { value: n.data } : { issues: n.error?.issues };
			} catch {
				return ze(e, t).then((e) => e.success ? { value: e.data } : { issues: e.error?.issues });
			}
		},
		vendor: "zod",
		version: 1
	}));
}), Ut = /*@__PURE__*/ s("$ZodString", (e, t) => {
	x.init(e, t), e._zod.pattern = [...e?._zod.bag?.patterns ?? []].pop() ?? yt(e._zod.bag), e._zod.parse = (n, r) => {
		if (t.coerce) try {
			n.value = String(n.value);
		} catch {}
		return typeof n.value == "string" || n.issues.push({
			expected: "string",
			code: "invalid_type",
			input: n.value,
			inst: e
		}), n;
	};
}), S = /*@__PURE__*/ s("$ZodStringFormat", (e, t) => {
	Nt.init(e, t), Ut.init(e, t);
}), Wt = /*@__PURE__*/ s("$ZodGUID", (e, t) => {
	t.pattern ??= tt, S.init(e, t);
}), Gt = /*@__PURE__*/ s("$ZodUUID", (e, t) => {
	if (t.version) {
		let e = {
			v1: 1,
			v2: 2,
			v3: 3,
			v4: 4,
			v5: 5,
			v6: 6,
			v7: 7,
			v8: 8
		}[t.version];
		if (e === void 0) throw Error(`Invalid UUID version: "${t.version}"`);
		t.pattern ??= nt(e);
	} else t.pattern ??= nt();
	S.init(e, t);
}), Kt = /*@__PURE__*/ s("$ZodEmail", (e, t) => {
	t.pattern ??= rt, S.init(e, t);
}), qt = /*@__PURE__*/ s("$ZodURL", (e, t) => {
	S.init(e, t), e._zod.check = (n) => {
		try {
			let r = n.value.trim();
			if (!t.normalize && t.protocol?.source === ft.source && !/^https?:\/\//i.test(r)) {
				n.issues.push({
					code: "invalid_format",
					format: "url",
					note: "Invalid URL format",
					input: n.value,
					inst: e,
					continue: !t.abort
				});
				return;
			}
			let i = new URL(r);
			t.hostname && (t.hostname.lastIndex = 0, t.hostname.test(i.hostname) || n.issues.push({
				code: "invalid_format",
				format: "url",
				note: "Invalid hostname",
				pattern: t.hostname.source,
				input: n.value,
				inst: e,
				continue: !t.abort
			})), t.protocol && (t.protocol.lastIndex = 0, t.protocol.test(i.protocol.endsWith(":") ? i.protocol.slice(0, -1) : i.protocol) || n.issues.push({
				code: "invalid_format",
				format: "url",
				note: "Invalid protocol",
				pattern: t.protocol.source,
				input: n.value,
				inst: e,
				continue: !t.abort
			})), n.value = t.normalize ? i.href : r;
			return;
		} catch {
			n.issues.push({
				code: "invalid_format",
				format: "url",
				input: n.value,
				inst: e,
				continue: !t.abort
			});
		}
	};
}), Jt = /*@__PURE__*/ s("$ZodEmoji", (e, t) => {
	t.pattern ??= at(), S.init(e, t);
}), Yt = /*@__PURE__*/ s("$ZodNanoID", (e, t) => {
	t.pattern ??= $e, S.init(e, t);
}), Xt = /*@__PURE__*/ s("$ZodCUID", (e, t) => {
	t.pattern ??= Je, S.init(e, t);
}), Zt = /*@__PURE__*/ s("$ZodCUID2", (e, t) => {
	t.pattern ??= Ye, S.init(e, t);
}), Qt = /*@__PURE__*/ s("$ZodULID", (e, t) => {
	t.pattern ??= Xe, S.init(e, t);
}), $t = /*@__PURE__*/ s("$ZodXID", (e, t) => {
	t.pattern ??= Ze, S.init(e, t);
}), en = /*@__PURE__*/ s("$ZodKSUID", (e, t) => {
	t.pattern ??= Qe, S.init(e, t);
}), tn = /*@__PURE__*/ s("$ZodISODateTime", (e, t) => {
	t.pattern ??= vt(t), S.init(e, t);
}), nn = /*@__PURE__*/ s("$ZodISODate", (e, t) => {
	t.pattern ??= ht, S.init(e, t);
}), rn = /*@__PURE__*/ s("$ZodISOTime", (e, t) => {
	t.pattern ??= _t(t), S.init(e, t);
}), an = /*@__PURE__*/ s("$ZodISODuration", (e, t) => {
	t.pattern ??= et, S.init(e, t);
}), on = /*@__PURE__*/ s("$ZodIPv4", (e, t) => {
	t.pattern ??= ot, S.init(e, t), e._zod.bag.format = "ipv4";
}), sn = /*@__PURE__*/ s("$ZodIPv6", (e, t) => {
	t.pattern ??= st, S.init(e, t), e._zod.bag.format = "ipv6", e._zod.check = (n) => {
		try {
			new URL(`http://[${n.value}]`);
		} catch {
			n.issues.push({
				code: "invalid_format",
				format: "ipv6",
				input: n.value,
				inst: e,
				continue: !t.abort
			});
		}
	};
}), cn = /*@__PURE__*/ s("$ZodCIDRv4", (e, t) => {
	t.pattern ??= ct, S.init(e, t);
}), ln = /*@__PURE__*/ s("$ZodCIDRv6", (e, t) => {
	t.pattern ??= lt, S.init(e, t), e._zod.check = (n) => {
		let r = n.value.split("/");
		try {
			if (r.length !== 2) throw Error();
			let [e, t] = r;
			if (!t) throw Error();
			let n = Number(t);
			if (`${n}` !== t || n < 0 || n > 128) throw Error();
			new URL(`http://[${e}]`);
		} catch {
			n.issues.push({
				code: "invalid_format",
				format: "cidrv6",
				input: n.value,
				inst: e,
				continue: !t.abort
			});
		}
	};
});
function un(e) {
	if (e === "") return !0;
	if (/\s/.test(e) || e.length % 4 != 0) return !1;
	try {
		return atob(e), !0;
	} catch {
		return !1;
	}
}
var dn = /*@__PURE__*/ s("$ZodBase64", (e, t) => {
	t.pattern ??= ut, S.init(e, t), e._zod.bag.contentEncoding = "base64", e._zod.check = (n) => {
		un(n.value) || n.issues.push({
			code: "invalid_format",
			format: "base64",
			input: n.value,
			inst: e,
			continue: !t.abort
		});
	};
});
function fn(e) {
	if (!dt.test(e)) return !1;
	let t = e.replace(/[-_]/g, (e) => e === "-" ? "+" : "/");
	return un(t.padEnd(Math.ceil(t.length / 4) * 4, "="));
}
var pn = /*@__PURE__*/ s("$ZodBase64URL", (e, t) => {
	t.pattern ??= dt, S.init(e, t), e._zod.bag.contentEncoding = "base64url", e._zod.check = (n) => {
		fn(n.value) || n.issues.push({
			code: "invalid_format",
			format: "base64url",
			input: n.value,
			inst: e,
			continue: !t.abort
		});
	};
}), mn = /*@__PURE__*/ s("$ZodE164", (e, t) => {
	t.pattern ??= pt, S.init(e, t);
});
function hn(e, t = null) {
	try {
		let n = e.split(".");
		if (n.length !== 3) return !1;
		let [r] = n;
		if (!r) return !1;
		let i = JSON.parse(atob(r));
		return !("typ" in i && i?.typ !== "JWT" || !i.alg || t && (!("alg" in i) || i.alg !== t));
	} catch {
		return !1;
	}
}
var gn = /*@__PURE__*/ s("$ZodJWT", (e, t) => {
	S.init(e, t), e._zod.check = (n) => {
		hn(n.value, t.alg) || n.issues.push({
			code: "invalid_format",
			format: "jwt",
			input: n.value,
			inst: e,
			continue: !t.abort
		});
	};
}), _n = /*@__PURE__*/ s("$ZodNumber", (e, t) => {
	x.init(e, t), e._zod.pattern = e._zod.bag.pattern ?? xt, e._zod.parse = (n, r) => {
		if (t.coerce) try {
			n.value = Number(n.value);
		} catch {}
		let i = n.value;
		if (typeof i == "number" && !Number.isNaN(i) && Number.isFinite(i)) return n;
		let a = typeof i == "number" ? Number.isNaN(i) ? "NaN" : Number.isFinite(i) ? void 0 : "Infinity" : void 0;
		return n.issues.push({
			expected: "number",
			code: "invalid_type",
			input: i,
			inst: e,
			...a ? { received: a } : {}
		}), n;
	};
}), vn = /*@__PURE__*/ s("$ZodNumberFormat", (e, t) => {
	kt.init(e, t), _n.init(e, t);
}), yn = /*@__PURE__*/ s("$ZodBoolean", (e, t) => {
	x.init(e, t), e._zod.pattern = St, e._zod.parse = (n, r) => {
		if (t.coerce) try {
			n.value = !!n.value;
		} catch {}
		let i = n.value;
		return typeof i == "boolean" || n.issues.push({
			expected: "boolean",
			code: "invalid_type",
			input: i,
			inst: e
		}), n;
	};
}), bn = /*@__PURE__*/ s("$ZodUnknown", (e, t) => {
	x.init(e, t), e._zod.parse = (e) => e;
}), xn = /*@__PURE__*/ s("$ZodNever", (e, t) => {
	x.init(e, t), e._zod.parse = (t, n) => (t.issues.push({
		expected: "never",
		code: "invalid_type",
		input: t.value,
		inst: e
	}), t);
});
function Sn(e, t, n) {
	e.issues.length && t.issues.push(...Te(n, e.issues)), t.value[n] = e.value;
}
var Cn = /*@__PURE__*/ s("$ZodArray", (e, t) => {
	x.init(e, t), e._zod.parse = (n, r) => {
		let i = n.value;
		if (!Array.isArray(i)) return n.issues.push({
			expected: "array",
			code: "invalid_type",
			input: i,
			inst: e
		}), n;
		n.value = Array(i.length);
		let a = [];
		for (let e = 0; e < i.length; e++) {
			let o = i[e], s = t.element._zod.run({
				value: o,
				issues: []
			}, r);
			s instanceof Promise ? a.push(s.then((t) => Sn(t, n, e))) : Sn(s, n, e);
		}
		return a.length ? Promise.all(a).then(() => n) : n;
	};
});
function wn(e, t, n, r, i, a) {
	let o = n in r;
	if (e.issues.length) {
		if (i && a && !o) return;
		t.issues.push(...Te(n, e.issues));
	}
	if (!o && !i) {
		e.issues.length || t.issues.push({
			code: "invalid_type",
			expected: "nonoptional",
			input: void 0,
			path: [n]
		});
		return;
	}
	e.value === void 0 ? o && (t.value[n] = void 0) : t.value[n] = e.value;
}
function Tn(e) {
	let t = Object.keys(e.shape);
	for (let n of t) if (!e.shape?.[n]?._zod?.traits?.has("$ZodType")) throw Error(`Invalid element at key "${n}": expected a Zod schema`);
	let n = me(e.shape);
	return {
		...e,
		keys: t,
		keySet: new Set(t),
		numKeys: t.length,
		optionalKeys: new Set(n)
	};
}
function En(e, t, n, r, i, a) {
	let o = [], s = i.keySet, c = i.catchall._zod, l = c.def.type, u = c.optin === "optional", d = c.optout === "optional";
	for (let i in t) {
		if (i === "__proto__" || s.has(i)) continue;
		if (l === "never") {
			o.push(i);
			continue;
		}
		let a = c.run({
			value: t[i],
			issues: []
		}, r);
		a instanceof Promise ? e.push(a.then((e) => wn(e, n, i, t, u, d))) : wn(a, n, i, t, u, d);
	}
	return o.length && n.issues.push({
		code: "unrecognized_keys",
		keys: o,
		input: t,
		inst: a
	}), e.length ? Promise.all(e).then(() => n) : n;
}
var Dn = /*@__PURE__*/ s("$ZodObject", (e, t) => {
	if (x.init(e, t), !Object.getOwnPropertyDescriptor(t, "shape")?.get) {
		let e = t.shape;
		Object.defineProperty(t, "shape", { get: () => {
			let n = { ...e };
			return Object.defineProperty(t, "shape", { value: n }), n;
		} });
	}
	let n = ee(() => Tn(t));
	m(e._zod, "propValues", () => {
		let e = t.shape, n = {};
		for (let t in e) {
			let r = e[t]._zod;
			if (r.values) {
				n[t] ?? (n[t] = /* @__PURE__ */ new Set());
				for (let e of r.values) n[t].add(e);
			}
		}
		return n;
	});
	let r = ce, i = t.catchall, a;
	e._zod.parse = (t, o) => {
		a ??= n.value;
		let s = t.value;
		if (!r(s)) return t.issues.push({
			expected: "object",
			code: "invalid_type",
			input: s,
			inst: e
		}), t;
		t.value = {};
		let c = [], l = a.shape;
		for (let e of a.keys) {
			let n = l[e], r = n._zod.optin === "optional", i = n._zod.optout === "optional", a = n._zod.run({
				value: s[e],
				issues: []
			}, o);
			a instanceof Promise ? c.push(a.then((n) => wn(n, t, e, s, r, i))) : wn(a, t, e, s, r, i);
		}
		return i ? En(c, s, t, o, n.value, e) : c.length ? Promise.all(c).then(() => t) : t;
	};
}), On = /*@__PURE__*/ s("$ZodObjectJIT", (e, t) => {
	Dn.init(e, t);
	let n = e._zod.parse, r = ee(() => Tn(t)), i = (e) => {
		let t = new Vt([
			"shape",
			"payload",
			"ctx"
		]), n = r.value, i = (e) => {
			let t = ae(e);
			return `shape[${t}]._zod.run({ value: input[${t}], issues: [] }, ctx)`;
		};
		t.write("const input = payload.value;");
		let a = Object.create(null), o = 0;
		for (let e of n.keys) a[e] = `key_${o++}`;
		t.write("const newResult = {};");
		for (let r of n.keys) {
			let n = a[r], o = ae(r), s = e[r], c = s?._zod?.optin === "optional", l = s?._zod?.optout === "optional";
			t.write(`const ${n} = ${i(r)};`), c && l ? t.write(`
        if (${n}.issues.length) {
          if (${o} in input) {
            payload.issues = payload.issues.concat(${n}.issues.map(iss => ({
              ...iss,
              path: iss.path ? [${o}, ...iss.path] : [${o}]
            })));
          }
        }
        
        if (${n}.value === undefined) {
          if (${o} in input) {
            newResult[${o}] = undefined;
          }
        } else {
          newResult[${o}] = ${n}.value;
        }
        
      `) : c ? t.write(`
        if (${n}.issues.length) {
          payload.issues = payload.issues.concat(${n}.issues.map(iss => ({
            ...iss,
            path: iss.path ? [${o}, ...iss.path] : [${o}]
          })));
        }
        
        if (${n}.value === undefined) {
          if (${o} in input) {
            newResult[${o}] = undefined;
          }
        } else {
          newResult[${o}] = ${n}.value;
        }
        
      `) : t.write(`
        const ${n}_present = ${o} in input;
        if (${n}.issues.length) {
          payload.issues = payload.issues.concat(${n}.issues.map(iss => ({
            ...iss,
            path: iss.path ? [${o}, ...iss.path] : [${o}]
          })));
        }
        if (!${n}_present && !${n}.issues.length) {
          payload.issues.push({
            code: "invalid_type",
            expected: "nonoptional",
            input: undefined,
            path: [${o}]
          });
        }

        if (${n}_present) {
          if (${n}.value === undefined) {
            newResult[${o}] = undefined;
          } else {
            newResult[${o}] = ${n}.value;
          }
        }

      `);
		}
		t.write("payload.value = newResult;"), t.write("return payload;");
		let s = t.compile();
		return (t, n) => s(e, t, n);
	}, a, o = ce, s = !u.jitless, c = s && le.value, l = t.catchall, d;
	e._zod.parse = (u, f) => {
		d ??= r.value;
		let p = u.value;
		return o(p) ? s && c && f?.async === !1 && f.jitless !== !0 ? (a ||= i(t.shape), u = a(u, f), l ? En([], p, u, f, d, e) : u) : n(u, f) : (u.issues.push({
			expected: "object",
			code: "invalid_type",
			input: p,
			inst: e
		}), u);
	};
});
function kn(e, t, n, r) {
	for (let n of e) if (n.issues.length === 0) return t.value = n.value, t;
	let i = e.filter((e) => !Ce(e));
	return i.length === 1 ? (t.value = i[0].value, i[0]) : (t.issues.push({
		code: "invalid_union",
		input: t.value,
		inst: n,
		errors: e.map((e) => e.issues.map((e) => y(e, r, d())))
	}), t);
}
var An = /*@__PURE__*/ s("$ZodUnion", (e, t) => {
	x.init(e, t), m(e._zod, "optin", () => t.options.some((e) => e._zod.optin === "optional") ? "optional" : void 0), m(e._zod, "optout", () => t.options.some((e) => e._zod.optout === "optional") ? "optional" : void 0), m(e._zod, "values", () => {
		if (t.options.every((e) => e._zod.values)) return new Set(t.options.flatMap((e) => Array.from(e._zod.values)));
	}), m(e._zod, "pattern", () => {
		if (t.options.every((e) => e._zod.pattern)) {
			let e = t.options.map((e) => e._zod.pattern);
			return RegExp(`^(${e.map((e) => ne(e.source)).join("|")})$`);
		}
	});
	let n = t.options.length === 1 ? t.options[0]._zod.run : null;
	e._zod.parse = (r, i) => {
		if (n) return n(r, i);
		let a = !1, o = [];
		for (let e of t.options) {
			let t = e._zod.run({
				value: r.value,
				issues: []
			}, i);
			if (t instanceof Promise) o.push(t), a = !0;
			else {
				if (t.issues.length === 0) return t;
				o.push(t);
			}
		}
		return a ? Promise.all(o).then((t) => kn(t, r, e, i)) : kn(o, r, e, i);
	};
}), jn = /*@__PURE__*/ s("$ZodIntersection", (e, t) => {
	x.init(e, t), e._zod.parse = (e, n) => {
		let r = e.value, i = t.left._zod.run({
			value: r,
			issues: []
		}, n), a = t.right._zod.run({
			value: r,
			issues: []
		}, n);
		return i instanceof Promise || a instanceof Promise ? Promise.all([i, a]).then(([t, n]) => Nn(e, t, n)) : Nn(e, i, a);
	};
});
function Mn(e, t) {
	if (e === t || e instanceof Date && t instanceof Date && +e == +t) return {
		valid: !0,
		data: e
	};
	if (ue(e) && ue(t)) {
		let n = Object.keys(t), r = Object.keys(e).filter((e) => n.indexOf(e) !== -1), i = {
			...e,
			...t
		};
		for (let n of r) {
			let r = Mn(e[n], t[n]);
			if (!r.valid) return {
				valid: !1,
				mergeErrorPath: [n, ...r.mergeErrorPath]
			};
			i[n] = r.data;
		}
		return {
			valid: !0,
			data: i
		};
	}
	if (Array.isArray(e) && Array.isArray(t)) {
		if (e.length !== t.length) return {
			valid: !1,
			mergeErrorPath: []
		};
		let n = [];
		for (let r = 0; r < e.length; r++) {
			let i = e[r], a = t[r], o = Mn(i, a);
			if (!o.valid) return {
				valid: !1,
				mergeErrorPath: [r, ...o.mergeErrorPath]
			};
			n.push(o.data);
		}
		return {
			valid: !0,
			data: n
		};
	}
	return {
		valid: !1,
		mergeErrorPath: []
	};
}
function Nn(e, t, n) {
	let r = /* @__PURE__ */ new Map(), i;
	for (let n of t.issues) if (n.code === "unrecognized_keys") {
		i ??= n;
		for (let e of n.keys) r.has(e) || r.set(e, {}), r.get(e).l = !0;
	} else e.issues.push(n);
	for (let t of n.issues) if (t.code === "unrecognized_keys") for (let e of t.keys) r.has(e) || r.set(e, {}), r.get(e).r = !0;
	else e.issues.push(t);
	let a = [...r].filter(([, e]) => e.l && e.r).map(([e]) => e);
	if (a.length && i && e.issues.push({
		...i,
		keys: a
	}), Ce(e)) return e;
	let o = Mn(t.value, n.value);
	if (!o.valid) throw Error(`Unmergable intersection. Error path: ${JSON.stringify(o.mergeErrorPath)}`);
	return e.value = o.data, e;
}
var Pn = /*@__PURE__*/ s("$ZodRecord", (e, t) => {
	x.init(e, t), e._zod.parse = (n, r) => {
		let i = n.value;
		if (!ue(i)) return n.issues.push({
			expected: "record",
			code: "invalid_type",
			input: i,
			inst: e
		}), n;
		let a = [], o = t.keyType._zod.values;
		if (o) {
			n.value = {};
			let s = /* @__PURE__ */ new Set();
			for (let c of o) if (typeof c == "string" || typeof c == "number" || typeof c == "symbol") {
				s.add(typeof c == "number" ? c.toString() : c);
				let o = t.keyType._zod.run({
					value: c,
					issues: []
				}, r);
				if (o instanceof Promise) throw Error("Async schemas not supported in object keys currently");
				if (o.issues.length) {
					n.issues.push({
						code: "invalid_key",
						origin: "record",
						issues: o.issues.map((e) => y(e, r, d())),
						input: c,
						path: [c],
						inst: e
					});
					continue;
				}
				let l = o.value, u = t.valueType._zod.run({
					value: i[c],
					issues: []
				}, r);
				u instanceof Promise ? a.push(u.then((e) => {
					e.issues.length && n.issues.push(...Te(c, e.issues)), n.value[l] = e.value;
				})) : (u.issues.length && n.issues.push(...Te(c, u.issues)), n.value[l] = u.value);
			}
			let c;
			for (let e in i) s.has(e) || (c ??= [], c.push(e));
			c && c.length > 0 && n.issues.push({
				code: "unrecognized_keys",
				input: i,
				inst: e,
				keys: c
			});
		} else {
			n.value = {};
			for (let o of Reflect.ownKeys(i)) {
				if (o === "__proto__" || !Object.prototype.propertyIsEnumerable.call(i, o)) continue;
				let s = t.keyType._zod.run({
					value: o,
					issues: []
				}, r);
				if (s instanceof Promise) throw Error("Async schemas not supported in object keys currently");
				if (typeof o == "string" && xt.test(o) && s.issues.length) {
					let e = t.keyType._zod.run({
						value: Number(o),
						issues: []
					}, r);
					if (e instanceof Promise) throw Error("Async schemas not supported in object keys currently");
					e.issues.length === 0 && (s = e);
				}
				if (s.issues.length) {
					t.mode === "loose" ? n.value[o] = i[o] : n.issues.push({
						code: "invalid_key",
						origin: "record",
						issues: s.issues.map((e) => y(e, r, d())),
						input: o,
						path: [o],
						inst: e
					});
					continue;
				}
				let c = t.valueType._zod.run({
					value: i[o],
					issues: []
				}, r);
				c instanceof Promise ? a.push(c.then((e) => {
					e.issues.length && n.issues.push(...Te(o, e.issues)), n.value[s.value] = e.value;
				})) : (c.issues.length && n.issues.push(...Te(o, c.issues)), n.value[s.value] = c.value);
			}
		}
		return a.length ? Promise.all(a).then(() => n) : n;
	};
}), Fn = /*@__PURE__*/ s("$ZodEnum", (e, t) => {
	x.init(e, t);
	let n = f(t.entries), r = new Set(n);
	e._zod.values = r, e._zod.pattern = RegExp(`^(${n.filter((e) => fe.has(typeof e)).map((e) => typeof e == "string" ? pe(e) : e.toString()).join("|")})$`), e._zod.parse = (t, i) => {
		let a = t.value;
		return r.has(a) || t.issues.push({
			code: "invalid_value",
			values: n,
			input: a,
			inst: e
		}), t;
	};
}), In = /*@__PURE__*/ s("$ZodLiteral", (e, t) => {
	if (x.init(e, t), t.values.length === 0) throw Error("Cannot create literal schema with no valid values");
	let n = new Set(t.values);
	e._zod.values = n, e._zod.pattern = RegExp(`^(${t.values.map((e) => typeof e == "string" ? pe(e) : e ? pe(e.toString()) : String(e)).join("|")})$`), e._zod.parse = (r, i) => {
		let a = r.value;
		return n.has(a) || r.issues.push({
			code: "invalid_value",
			values: t.values,
			input: a,
			inst: e
		}), r;
	};
}), Ln = /*@__PURE__*/ s("$ZodTransform", (e, t) => {
	x.init(e, t), e._zod.optin = "optional", e._zod.parse = (n, r) => {
		if (r.direction === "backward") throw new l(e.constructor.name);
		let i = t.transform(n.value, n);
		if (r.async) return (i instanceof Promise ? i : Promise.resolve(i)).then((e) => (n.value = e, n.fallback = !0, n));
		if (i instanceof Promise) throw new c();
		return n.value = i, n.fallback = !0, n;
	};
});
function Rn(e, t) {
	return t === void 0 && (e.issues.length || e.fallback) ? {
		issues: [],
		value: void 0
	} : e;
}
var zn = /*@__PURE__*/ s("$ZodOptional", (e, t) => {
	x.init(e, t), e._zod.optin = "optional", e._zod.optout = "optional", m(e._zod, "values", () => t.innerType._zod.values ? /* @__PURE__ */ new Set([...t.innerType._zod.values, void 0]) : void 0), m(e._zod, "pattern", () => {
		let e = t.innerType._zod.pattern;
		return e ? RegExp(`^(${ne(e.source)})?$`) : void 0;
	}), e._zod.parse = (e, n) => {
		if (t.innerType._zod.optin === "optional") {
			let r = e.value, i = t.innerType._zod.run(e, n);
			return i instanceof Promise ? i.then((e) => Rn(e, r)) : Rn(i, r);
		}
		return e.value === void 0 ? e : t.innerType._zod.run(e, n);
	};
}), Bn = /*@__PURE__*/ s("$ZodExactOptional", (e, t) => {
	zn.init(e, t), m(e._zod, "values", () => t.innerType._zod.values), m(e._zod, "pattern", () => t.innerType._zod.pattern), e._zod.parse = (e, n) => t.innerType._zod.run(e, n);
}), Vn = /*@__PURE__*/ s("$ZodNullable", (e, t) => {
	x.init(e, t), m(e._zod, "optin", () => t.innerType._zod.optin), m(e._zod, "optout", () => t.innerType._zod.optout), m(e._zod, "pattern", () => {
		let e = t.innerType._zod.pattern;
		return e ? RegExp(`^(${ne(e.source)}|null)$`) : void 0;
	}), m(e._zod, "values", () => t.innerType._zod.values ? /* @__PURE__ */ new Set([...t.innerType._zod.values, null]) : void 0), e._zod.parse = (e, n) => e.value === null ? e : t.innerType._zod.run(e, n);
}), Hn = /*@__PURE__*/ s("$ZodDefault", (e, t) => {
	x.init(e, t), e._zod.optin = "optional", m(e._zod, "values", () => t.innerType._zod.values), e._zod.parse = (e, n) => {
		if (n.direction === "backward") return t.innerType._zod.run(e, n);
		if (e.value === void 0) return e.value = t.defaultValue, e;
		let r = t.innerType._zod.run(e, n);
		return r instanceof Promise ? r.then((e) => Un(e, t)) : Un(r, t);
	};
});
function Un(e, t) {
	return e.value === void 0 && (e.value = t.defaultValue), e;
}
var Wn = /*@__PURE__*/ s("$ZodPrefault", (e, t) => {
	x.init(e, t), e._zod.optin = "optional", m(e._zod, "values", () => t.innerType._zod.values), e._zod.parse = (e, n) => (n.direction === "backward" || e.value === void 0 && (e.value = t.defaultValue), t.innerType._zod.run(e, n));
}), Gn = /*@__PURE__*/ s("$ZodNonOptional", (e, t) => {
	x.init(e, t), m(e._zod, "values", () => {
		let e = t.innerType._zod.values;
		return e ? new Set([...e].filter((e) => e !== void 0)) : void 0;
	}), e._zod.parse = (n, r) => {
		let i = t.innerType._zod.run(n, r);
		return i instanceof Promise ? i.then((t) => Kn(t, e)) : Kn(i, e);
	};
});
function Kn(e, t) {
	return !e.issues.length && e.value === void 0 && e.issues.push({
		code: "invalid_type",
		expected: "nonoptional",
		input: e.value,
		inst: t
	}), e;
}
var qn = /*@__PURE__*/ s("$ZodCatch", (e, t) => {
	x.init(e, t), e._zod.optin = "optional", m(e._zod, "optout", () => t.innerType._zod.optout), m(e._zod, "values", () => t.innerType._zod.values), e._zod.parse = (e, n) => {
		if (n.direction === "backward") return t.innerType._zod.run(e, n);
		let r = t.innerType._zod.run(e, n);
		return r instanceof Promise ? r.then((r) => (e.value = r.value, r.issues.length && (e.value = t.catchValue({
			...e,
			error: { issues: r.issues.map((e) => y(e, n, d())) },
			input: e.value
		}), e.issues = [], e.fallback = !0), e)) : (e.value = r.value, r.issues.length && (e.value = t.catchValue({
			...e,
			error: { issues: r.issues.map((e) => y(e, n, d())) },
			input: e.value
		}), e.issues = [], e.fallback = !0), e);
	};
}), Jn = /*@__PURE__*/ s("$ZodPipe", (e, t) => {
	x.init(e, t), m(e._zod, "values", () => t.in._zod.values), m(e._zod, "optin", () => t.in._zod.optin), m(e._zod, "optout", () => t.out._zod.optout), m(e._zod, "propValues", () => t.in._zod.propValues), e._zod.parse = (e, n) => {
		if (n.direction === "backward") {
			let r = t.out._zod.run(e, n);
			return r instanceof Promise ? r.then((e) => Yn(e, t.in, n)) : Yn(r, t.in, n);
		}
		let r = t.in._zod.run(e, n);
		return r instanceof Promise ? r.then((e) => Yn(e, t.out, n)) : Yn(r, t.out, n);
	};
});
function Yn(e, t, n) {
	return e.issues.length ? (e.aborted = !0, e) : t._zod.run({
		value: e.value,
		issues: e.issues,
		fallback: e.fallback
	}, n);
}
var Xn = /*@__PURE__*/ s("$ZodReadonly", (e, t) => {
	x.init(e, t), m(e._zod, "propValues", () => t.innerType._zod.propValues), m(e._zod, "values", () => t.innerType._zod.values), m(e._zod, "optin", () => t.innerType?._zod?.optin), m(e._zod, "optout", () => t.innerType?._zod?.optout), e._zod.parse = (e, n) => {
		if (n.direction === "backward") return t.innerType._zod.run(e, n);
		let r = t.innerType._zod.run(e, n);
		return r instanceof Promise ? r.then(Zn) : Zn(r);
	};
});
function Zn(e) {
	return e.value = Object.freeze(e.value), e;
}
var Qn = /*@__PURE__*/ s("$ZodCustom", (e, t) => {
	b.init(e, t), x.init(e, t), e._zod.parse = (e, t) => e, e._zod.check = (n) => {
		let r = n.value, i = t.fn(r);
		if (i instanceof Promise) return i.then((t) => $n(t, n, r, e));
		$n(i, n, r, e);
	};
});
function $n(e, t, n, r) {
	if (!e) {
		let e = {
			code: "custom",
			input: n,
			inst: r,
			path: [...r._zod.def.path ?? []],
			continue: !r._zod.def.abort
		};
		r._zod.def.params && (e.params = r._zod.def.params), t.issues.push(Oe(e));
	}
}
//#endregion
//#region node_modules/.pnpm/zod@4.4.3/node_modules/zod/v4/core/registries.js
var er, tr = class {
	constructor() {
		this._map = /* @__PURE__ */ new WeakMap(), this._idmap = /* @__PURE__ */ new Map();
	}
	add(e, ...t) {
		let n = t[0];
		return this._map.set(e, n), n && typeof n == "object" && "id" in n && this._idmap.set(n.id, e), this;
	}
	clear() {
		return this._map = /* @__PURE__ */ new WeakMap(), this._idmap = /* @__PURE__ */ new Map(), this;
	}
	remove(e) {
		let t = this._map.get(e);
		return t && typeof t == "object" && "id" in t && this._idmap.delete(t.id), this._map.delete(e), this;
	}
	get(e) {
		let t = e._zod.parent;
		if (t) {
			let n = { ...this.get(t) ?? {} };
			delete n.id;
			let r = {
				...n,
				...this._map.get(e)
			};
			return Object.keys(r).length ? r : void 0;
		}
		return this._map.get(e);
	}
	has(e) {
		return this._map.has(e);
	}
};
function nr() {
	return new tr();
}
(er = globalThis).__zod_globalRegistry ?? (er.__zod_globalRegistry = nr());
var rr = globalThis.__zod_globalRegistry;
//#endregion
//#region node_modules/.pnpm/zod@4.4.3/node_modules/zod/v4/core/api.js
// @__NO_SIDE_EFFECTS__
function ir(e, t) {
	return new e({
		type: "string",
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function ar(e, t) {
	return new e({
		type: "string",
		format: "email",
		check: "string_format",
		abort: !1,
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function or(e, t) {
	return new e({
		type: "string",
		format: "guid",
		check: "string_format",
		abort: !1,
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function sr(e, t) {
	return new e({
		type: "string",
		format: "uuid",
		check: "string_format",
		abort: !1,
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function cr(e, t) {
	return new e({
		type: "string",
		format: "uuid",
		check: "string_format",
		abort: !1,
		version: "v4",
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function lr(e, t) {
	return new e({
		type: "string",
		format: "uuid",
		check: "string_format",
		abort: !1,
		version: "v6",
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function ur(e, t) {
	return new e({
		type: "string",
		format: "uuid",
		check: "string_format",
		abort: !1,
		version: "v7",
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function dr(e, t) {
	return new e({
		type: "string",
		format: "url",
		check: "string_format",
		abort: !1,
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function fr(e, t) {
	return new e({
		type: "string",
		format: "emoji",
		check: "string_format",
		abort: !1,
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function pr(e, t) {
	return new e({
		type: "string",
		format: "nanoid",
		check: "string_format",
		abort: !1,
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function mr(e, t) {
	return new e({
		type: "string",
		format: "cuid",
		check: "string_format",
		abort: !1,
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function hr(e, t) {
	return new e({
		type: "string",
		format: "cuid2",
		check: "string_format",
		abort: !1,
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function gr(e, t) {
	return new e({
		type: "string",
		format: "ulid",
		check: "string_format",
		abort: !1,
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function _r(e, t) {
	return new e({
		type: "string",
		format: "xid",
		check: "string_format",
		abort: !1,
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function vr(e, t) {
	return new e({
		type: "string",
		format: "ksuid",
		check: "string_format",
		abort: !1,
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function yr(e, t) {
	return new e({
		type: "string",
		format: "ipv4",
		check: "string_format",
		abort: !1,
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function br(e, t) {
	return new e({
		type: "string",
		format: "ipv6",
		check: "string_format",
		abort: !1,
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function xr(e, t) {
	return new e({
		type: "string",
		format: "cidrv4",
		check: "string_format",
		abort: !1,
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Sr(e, t) {
	return new e({
		type: "string",
		format: "cidrv6",
		check: "string_format",
		abort: !1,
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Cr(e, t) {
	return new e({
		type: "string",
		format: "base64",
		check: "string_format",
		abort: !1,
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function wr(e, t) {
	return new e({
		type: "string",
		format: "base64url",
		check: "string_format",
		abort: !1,
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Tr(e, t) {
	return new e({
		type: "string",
		format: "e164",
		check: "string_format",
		abort: !1,
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Er(e, t) {
	return new e({
		type: "string",
		format: "jwt",
		check: "string_format",
		abort: !1,
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Dr(e, t) {
	return new e({
		type: "string",
		format: "datetime",
		check: "string_format",
		offset: !1,
		local: !1,
		precision: null,
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Or(e, t) {
	return new e({
		type: "string",
		format: "date",
		check: "string_format",
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function kr(e, t) {
	return new e({
		type: "string",
		format: "time",
		check: "string_format",
		precision: null,
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Ar(e, t) {
	return new e({
		type: "string",
		format: "duration",
		check: "string_format",
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function jr(e, t) {
	return new e({
		type: "number",
		checks: [],
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Mr(e, t) {
	return new e({
		type: "number",
		check: "number_format",
		abort: !1,
		format: "safeint",
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Nr(e, t) {
	return new e({
		type: "boolean",
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Pr(e) {
	return new e({ type: "unknown" });
}
// @__NO_SIDE_EFFECTS__
function Fr(e, t) {
	return new e({
		type: "never",
		...v(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Ir(e, t) {
	return new Et({
		check: "less_than",
		...v(t),
		value: e,
		inclusive: !1
	});
}
// @__NO_SIDE_EFFECTS__
function Lr(e, t) {
	return new Et({
		check: "less_than",
		...v(t),
		value: e,
		inclusive: !0
	});
}
// @__NO_SIDE_EFFECTS__
function Rr(e, t) {
	return new Dt({
		check: "greater_than",
		...v(t),
		value: e,
		inclusive: !1
	});
}
// @__NO_SIDE_EFFECTS__
function zr(e, t) {
	return new Dt({
		check: "greater_than",
		...v(t),
		value: e,
		inclusive: !0
	});
}
// @__NO_SIDE_EFFECTS__
function Br(e, t) {
	return new Ot({
		check: "multiple_of",
		...v(t),
		value: e
	});
}
// @__NO_SIDE_EFFECTS__
function Vr(e, t) {
	return new At({
		check: "max_length",
		...v(t),
		maximum: e
	});
}
// @__NO_SIDE_EFFECTS__
function Hr(e, t) {
	return new jt({
		check: "min_length",
		...v(t),
		minimum: e
	});
}
// @__NO_SIDE_EFFECTS__
function Ur(e, t) {
	return new Mt({
		check: "length_equals",
		...v(t),
		length: e
	});
}
// @__NO_SIDE_EFFECTS__
function Wr(e, t) {
	return new Pt({
		check: "string_format",
		format: "regex",
		...v(t),
		pattern: e
	});
}
// @__NO_SIDE_EFFECTS__
function Gr(e) {
	return new Ft({
		check: "string_format",
		format: "lowercase",
		...v(e)
	});
}
// @__NO_SIDE_EFFECTS__
function Kr(e) {
	return new It({
		check: "string_format",
		format: "uppercase",
		...v(e)
	});
}
// @__NO_SIDE_EFFECTS__
function qr(e, t) {
	return new Lt({
		check: "string_format",
		format: "includes",
		...v(t),
		includes: e
	});
}
// @__NO_SIDE_EFFECTS__
function Jr(e, t) {
	return new Rt({
		check: "string_format",
		format: "starts_with",
		...v(t),
		prefix: e
	});
}
// @__NO_SIDE_EFFECTS__
function Yr(e, t) {
	return new zt({
		check: "string_format",
		format: "ends_with",
		...v(t),
		suffix: e
	});
}
// @__NO_SIDE_EFFECTS__
function Xr(e) {
	return new Bt({
		check: "overwrite",
		tx: e
	});
}
// @__NO_SIDE_EFFECTS__
function Zr(e) {
	return /* @__PURE__ */ Xr((t) => t.normalize(e));
}
// @__NO_SIDE_EFFECTS__
function Qr() {
	return /* @__PURE__ */ Xr((e) => e.trim());
}
// @__NO_SIDE_EFFECTS__
function $r() {
	return /* @__PURE__ */ Xr((e) => e.toLowerCase());
}
// @__NO_SIDE_EFFECTS__
function ei() {
	return /* @__PURE__ */ Xr((e) => e.toUpperCase());
}
// @__NO_SIDE_EFFECTS__
function ti() {
	return /* @__PURE__ */ Xr((e) => oe(e));
}
// @__NO_SIDE_EFFECTS__
function ni(e, t, n) {
	return new e({
		type: "array",
		element: t,
		...v(n)
	});
}
// @__NO_SIDE_EFFECTS__
function ri(e, t, n) {
	return new e({
		type: "custom",
		check: "custom",
		fn: t,
		...v(n)
	});
}
// @__NO_SIDE_EFFECTS__
function ii(e, t) {
	let n = /* @__PURE__ */ ai((t) => (t.addIssue = (e) => {
		if (typeof e == "string") t.issues.push(Oe(e, t.value, n._zod.def));
		else {
			let r = e;
			r.fatal && (r.continue = !1), r.code ??= "custom", r.input ??= t.value, r.inst ??= n, r.continue ??= !n._zod.def.abort, t.issues.push(Oe(r));
		}
	}, e(t.value, t)), t);
	return n;
}
// @__NO_SIDE_EFFECTS__
function ai(e, t) {
	let n = new b({
		check: "custom",
		...v(t)
	});
	return n._zod.check = e, n;
}
//#endregion
//#region node_modules/.pnpm/zod@4.4.3/node_modules/zod/v4/core/to-json-schema.js
function oi(e) {
	let t = e?.target ?? "draft-2020-12";
	return t === "draft-4" && (t = "draft-04"), t === "draft-7" && (t = "draft-07"), {
		processors: e.processors ?? {},
		metadataRegistry: e?.metadata ?? rr,
		target: t,
		unrepresentable: e?.unrepresentable ?? "throw",
		override: e?.override ?? (() => {}),
		io: e?.io ?? "output",
		counter: 0,
		seen: /* @__PURE__ */ new Map(),
		cycles: e?.cycles ?? "ref",
		reused: e?.reused ?? "inline",
		external: e?.external ?? void 0
	};
}
function C(e, t, n = {
	path: [],
	schemaPath: []
}) {
	var r;
	let i = e._zod.def, a = t.seen.get(e);
	if (a) return a.count++, n.schemaPath.includes(e) && (a.cycle = n.path), a.schema;
	let o = {
		schema: {},
		count: 1,
		cycle: void 0,
		path: n.path
	};
	t.seen.set(e, o);
	let s = e._zod.toJSONSchema?.();
	if (s) o.schema = s;
	else {
		let r = {
			...n,
			schemaPath: [...n.schemaPath, e],
			path: n.path
		};
		if (e._zod.processJSONSchema) e._zod.processJSONSchema(t, o.schema, r);
		else {
			let n = o.schema, a = t.processors[i.type];
			if (!a) throw Error(`[toJSONSchema]: Non-representable type encountered: ${i.type}`);
			a(e, t, n, r);
		}
		let a = e._zod.parent;
		a && (o.ref ||= a, C(a, t, r), t.seen.get(a).isParent = !0);
	}
	let c = t.metadataRegistry.get(e);
	return c && Object.assign(o.schema, c), t.io === "input" && w(e) && (delete o.schema.examples, delete o.schema.default), t.io === "input" && "_prefault" in o.schema && ((r = o.schema).default ?? (r.default = o.schema._prefault)), delete o.schema._prefault, t.seen.get(e).schema;
}
function si(e, t) {
	let n = e.seen.get(t);
	if (!n) throw Error("Unprocessed schema. This is a bug in Zod.");
	let r = /* @__PURE__ */ new Map();
	for (let t of e.seen.entries()) {
		let n = e.metadataRegistry.get(t[0])?.id;
		if (n) {
			let e = r.get(n);
			if (e && e !== t[0]) throw Error(`Duplicate schema id "${n}" detected during JSON Schema conversion. Two different schemas cannot share the same id when converted together.`);
			r.set(n, t[0]);
		}
	}
	let i = (t) => {
		let r = e.target === "draft-2020-12" ? "$defs" : "definitions";
		if (e.external) {
			let n = e.external.registry.get(t[0])?.id, i = e.external.uri ?? ((e) => e);
			if (n) return { ref: i(n) };
			let a = t[1].defId ?? t[1].schema.id ?? `schema${e.counter++}`;
			return t[1].defId = a, {
				defId: a,
				ref: `${i("__shared")}#/${r}/${a}`
			};
		}
		if (t[1] === n) return { ref: "#" };
		let i = `#/${r}/`, a = t[1].schema.id ?? `__schema${e.counter++}`;
		return {
			defId: a,
			ref: i + a
		};
	}, a = (e) => {
		if (e[1].schema.$ref) return;
		let t = e[1], { ref: n, defId: r } = i(e);
		t.def = { ...t.schema }, r && (t.defId = r);
		let a = t.schema;
		for (let e in a) delete a[e];
		a.$ref = n;
	};
	if (e.cycles === "throw") for (let t of e.seen.entries()) {
		let e = t[1];
		if (e.cycle) throw Error(`Cycle detected: #/${e.cycle?.join("/")}/<root>

Set the \`cycles\` parameter to \`"ref"\` to resolve cyclical schemas with defs.`);
	}
	for (let n of e.seen.entries()) {
		let r = n[1];
		if (t === n[0]) {
			a(n);
			continue;
		}
		if (e.external) {
			let r = e.external.registry.get(n[0])?.id;
			if (t !== n[0] && r) {
				a(n);
				continue;
			}
		}
		if (e.metadataRegistry.get(n[0])?.id) {
			a(n);
			continue;
		}
		if (r.cycle) {
			a(n);
			continue;
		}
		if (r.count > 1 && e.reused === "ref") {
			a(n);
			continue;
		}
	}
}
function ci(e, t) {
	let n = e.seen.get(t);
	if (!n) throw Error("Unprocessed schema. This is a bug in Zod.");
	let r = (t) => {
		let n = e.seen.get(t);
		if (n.ref === null) return;
		let i = n.def ?? n.schema, a = { ...i }, o = n.ref;
		if (n.ref = null, o) {
			r(o);
			let n = e.seen.get(o), s = n.schema;
			if (s.$ref && (e.target === "draft-07" || e.target === "draft-04" || e.target === "openapi-3.0") ? (i.allOf = i.allOf ?? [], i.allOf.push(s)) : Object.assign(i, s), Object.assign(i, a), t._zod.parent === o) for (let e in i) e !== "$ref" && e !== "allOf" && (e in a || delete i[e]);
			if (s.$ref && n.def) for (let e in i) e !== "$ref" && e !== "allOf" && e in n.def && JSON.stringify(i[e]) === JSON.stringify(n.def[e]) && delete i[e];
		}
		let s = t._zod.parent;
		if (s && s !== o) {
			r(s);
			let t = e.seen.get(s);
			if (t?.schema.$ref && (i.$ref = t.schema.$ref, t.def)) for (let e in i) e !== "$ref" && e !== "allOf" && e in t.def && JSON.stringify(i[e]) === JSON.stringify(t.def[e]) && delete i[e];
		}
		e.override({
			zodSchema: t,
			jsonSchema: i,
			path: n.path ?? []
		});
	};
	for (let t of [...e.seen.entries()].reverse()) r(t[0]);
	let i = {};
	if (e.target === "draft-2020-12" ? i.$schema = "https://json-schema.org/draft/2020-12/schema" : e.target === "draft-07" ? i.$schema = "http://json-schema.org/draft-07/schema#" : e.target === "draft-04" ? i.$schema = "http://json-schema.org/draft-04/schema#" : e.target, e.external?.uri) {
		let n = e.external.registry.get(t)?.id;
		if (!n) throw Error("Schema is missing an `id` property");
		i.$id = e.external.uri(n);
	}
	Object.assign(i, n.def ?? n.schema);
	let a = e.metadataRegistry.get(t)?.id;
	a !== void 0 && i.id === a && delete i.id;
	let o = e.external?.defs ?? {};
	for (let t of e.seen.entries()) {
		let e = t[1];
		e.def && e.defId && (e.def.id === e.defId && delete e.def.id, o[e.defId] = e.def);
	}
	e.external || Object.keys(o).length > 0 && (e.target === "draft-2020-12" ? i.$defs = o : i.definitions = o);
	try {
		let n = JSON.parse(JSON.stringify(i));
		return Object.defineProperty(n, "~standard", {
			value: {
				...t["~standard"],
				jsonSchema: {
					input: ui(t, "input", e.processors),
					output: ui(t, "output", e.processors)
				}
			},
			enumerable: !1,
			writable: !1
		}), n;
	} catch {
		throw Error("Error converting schema to JSON.");
	}
}
function w(e, t) {
	let n = t ?? { seen: /* @__PURE__ */ new Set() };
	if (n.seen.has(e)) return !1;
	n.seen.add(e);
	let r = e._zod.def;
	if (r.type === "transform") return !0;
	if (r.type === "array") return w(r.element, n);
	if (r.type === "set") return w(r.valueType, n);
	if (r.type === "lazy") return w(r.getter(), n);
	if (r.type === "promise" || r.type === "optional" || r.type === "nonoptional" || r.type === "nullable" || r.type === "readonly" || r.type === "default" || r.type === "prefault") return w(r.innerType, n);
	if (r.type === "intersection") return w(r.left, n) || w(r.right, n);
	if (r.type === "record" || r.type === "map") return w(r.keyType, n) || w(r.valueType, n);
	if (r.type === "pipe") return e._zod.traits.has("$ZodCodec") ? !0 : w(r.in, n) || w(r.out, n);
	if (r.type === "object") {
		for (let e in r.shape) if (w(r.shape[e], n)) return !0;
		return !1;
	}
	if (r.type === "union") {
		for (let e of r.options) if (w(e, n)) return !0;
		return !1;
	}
	if (r.type === "tuple") {
		for (let e of r.items) if (w(e, n)) return !0;
		return !!(r.rest && w(r.rest, n));
	}
	return !1;
}
var li = (e, t = {}) => (n) => {
	let r = oi({
		...n,
		processors: t
	});
	return C(e, r), si(r, e), ci(r, e);
}, ui = (e, t, n = {}) => (r) => {
	let { libraryOptions: i, target: a } = r ?? {}, o = oi({
		...i ?? {},
		target: a,
		io: t,
		processors: n
	});
	return C(e, o), si(o, e), ci(o, e);
}, di = {
	guid: "uuid",
	url: "uri",
	datetime: "date-time",
	json_string: "json-string",
	regex: ""
}, fi = (e, t, n, r) => {
	let i = n;
	i.type = "string";
	let { minimum: a, maximum: o, format: s, patterns: c, contentEncoding: l } = e._zod.bag;
	if (typeof a == "number" && (i.minLength = a), typeof o == "number" && (i.maxLength = o), s && (i.format = di[s] ?? s, i.format === "" && delete i.format, s === "time" && delete i.format), l && (i.contentEncoding = l), c && c.size > 0) {
		let e = [...c];
		e.length === 1 ? i.pattern = e[0].source : e.length > 1 && (i.allOf = [...e.map((e) => ({
			...t.target === "draft-07" || t.target === "draft-04" || t.target === "openapi-3.0" ? { type: "string" } : {},
			pattern: e.source
		}))]);
	}
}, pi = (e, t, n, r) => {
	let i = n, { minimum: a, maximum: o, format: s, multipleOf: c, exclusiveMaximum: l, exclusiveMinimum: u } = e._zod.bag;
	i.type = typeof s == "string" && s.includes("int") ? "integer" : "number";
	let d = typeof u == "number" && u >= (a ?? -Infinity), f = typeof l == "number" && l <= (o ?? Infinity), p = t.target === "draft-04" || t.target === "openapi-3.0";
	d ? p ? (i.minimum = u, i.exclusiveMinimum = !0) : i.exclusiveMinimum = u : typeof a == "number" && (i.minimum = a), f ? p ? (i.maximum = l, i.exclusiveMaximum = !0) : i.exclusiveMaximum = l : typeof o == "number" && (i.maximum = o), typeof c == "number" && (i.multipleOf = c);
}, mi = (e, t, n, r) => {
	n.type = "boolean";
}, hi = (e, t, n, r) => {
	n.not = {};
}, gi = (e, t, n, r) => {
	let i = e._zod.def, a = f(i.entries);
	a.every((e) => typeof e == "number") && (n.type = "number"), a.every((e) => typeof e == "string") && (n.type = "string"), n.enum = a;
}, _i = (e, t, n, r) => {
	let i = e._zod.def, a = [];
	for (let e of i.values) if (e === void 0) {
		if (t.unrepresentable === "throw") throw Error("Literal `undefined` cannot be represented in JSON Schema");
	} else if (typeof e == "bigint") {
		if (t.unrepresentable === "throw") throw Error("BigInt literals cannot be represented in JSON Schema");
		a.push(Number(e));
	} else a.push(e);
	if (a.length !== 0) {
		if (a.length === 1) {
			let e = a[0];
			n.type = e === null ? "null" : typeof e, t.target === "draft-04" || t.target === "openapi-3.0" ? n.enum = [e] : n.const = e;
		} else a.every((e) => typeof e == "number") && (n.type = "number"), a.every((e) => typeof e == "string") && (n.type = "string"), a.every((e) => typeof e == "boolean") && (n.type = "boolean"), a.every((e) => e === null) && (n.type = "null"), n.enum = a;
	}
}, vi = (e, t, n, r) => {
	if (t.unrepresentable === "throw") throw Error("Custom types cannot be represented in JSON Schema");
}, yi = (e, t, n, r) => {
	if (t.unrepresentable === "throw") throw Error("Transforms cannot be represented in JSON Schema");
}, bi = (e, t, n, r) => {
	let i = n, a = e._zod.def, { minimum: o, maximum: s } = e._zod.bag;
	typeof o == "number" && (i.minItems = o), typeof s == "number" && (i.maxItems = s), i.type = "array", i.items = C(a.element, t, {
		...r,
		path: [...r.path, "items"]
	});
}, xi = (e, t, n, r) => {
	let i = n, a = e._zod.def;
	i.type = "object", i.properties = {};
	let o = a.shape;
	for (let e in o) i.properties[e] = C(o[e], t, {
		...r,
		path: [
			...r.path,
			"properties",
			e
		]
	});
	let s = new Set(Object.keys(o)), c = new Set([...s].filter((e) => {
		let n = a.shape[e]._zod;
		return t.io === "input" ? n.optin === void 0 : n.optout === void 0;
	}));
	c.size > 0 && (i.required = Array.from(c)), a.catchall?._zod.def.type === "never" ? i.additionalProperties = !1 : a.catchall ? a.catchall && (i.additionalProperties = C(a.catchall, t, {
		...r,
		path: [...r.path, "additionalProperties"]
	})) : t.io === "output" && (i.additionalProperties = !1);
}, Si = (e, t, n, r) => {
	let i = e._zod.def, a = i.inclusive === !1, o = i.options.map((e, n) => C(e, t, {
		...r,
		path: [
			...r.path,
			a ? "oneOf" : "anyOf",
			n
		]
	}));
	a ? n.oneOf = o : n.anyOf = o;
}, Ci = (e, t, n, r) => {
	let i = e._zod.def, a = C(i.left, t, {
		...r,
		path: [
			...r.path,
			"allOf",
			0
		]
	}), o = C(i.right, t, {
		...r,
		path: [
			...r.path,
			"allOf",
			1
		]
	}), s = (e) => "allOf" in e && Object.keys(e).length === 1;
	n.allOf = [...s(a) ? a.allOf : [a], ...s(o) ? o.allOf : [o]];
}, wi = (e, t, n, r) => {
	let i = n, a = e._zod.def;
	i.type = "object";
	let o = a.keyType, s = o._zod.bag?.patterns;
	if (a.mode === "loose" && s && s.size > 0) {
		let e = C(a.valueType, t, {
			...r,
			path: [
				...r.path,
				"patternProperties",
				"*"
			]
		});
		i.patternProperties = {};
		for (let t of s) i.patternProperties[t.source] = e;
	} else (t.target === "draft-07" || t.target === "draft-2020-12") && (i.propertyNames = C(a.keyType, t, {
		...r,
		path: [...r.path, "propertyNames"]
	})), i.additionalProperties = C(a.valueType, t, {
		...r,
		path: [...r.path, "additionalProperties"]
	});
	let c = o._zod.values;
	if (c) {
		let e = [...c].filter((e) => typeof e == "string" || typeof e == "number");
		e.length > 0 && (i.required = e);
	}
}, Ti = (e, t, n, r) => {
	let i = e._zod.def, a = C(i.innerType, t, r), o = t.seen.get(e);
	t.target === "openapi-3.0" ? (o.ref = i.innerType, n.nullable = !0) : n.anyOf = [a, { type: "null" }];
}, Ei = (e, t, n, r) => {
	let i = e._zod.def;
	C(i.innerType, t, r);
	let a = t.seen.get(e);
	a.ref = i.innerType;
}, Di = (e, t, n, r) => {
	let i = e._zod.def;
	C(i.innerType, t, r);
	let a = t.seen.get(e);
	a.ref = i.innerType, n.default = JSON.parse(JSON.stringify(i.defaultValue));
}, Oi = (e, t, n, r) => {
	let i = e._zod.def;
	C(i.innerType, t, r);
	let a = t.seen.get(e);
	a.ref = i.innerType, t.io === "input" && (n._prefault = JSON.parse(JSON.stringify(i.defaultValue)));
}, ki = (e, t, n, r) => {
	let i = e._zod.def;
	C(i.innerType, t, r);
	let a = t.seen.get(e);
	a.ref = i.innerType;
	let o;
	try {
		o = i.catchValue(void 0);
	} catch {
		throw Error("Dynamic catch values are not supported in JSON Schema");
	}
	n.default = o;
}, Ai = (e, t, n, r) => {
	let i = e._zod.def, a = i.in._zod.traits.has("$ZodTransform"), o = t.io === "input" ? a ? i.out : i.in : i.out;
	C(o, t, r);
	let s = t.seen.get(e);
	s.ref = o;
}, ji = (e, t, n, r) => {
	let i = e._zod.def;
	C(i.innerType, t, r);
	let a = t.seen.get(e);
	a.ref = i.innerType, n.readOnly = !0;
}, Mi = (e, t, n, r) => {
	let i = e._zod.def;
	C(i.innerType, t, r);
	let a = t.seen.get(e);
	a.ref = i.innerType;
}, Ni = /*@__PURE__*/ s("ZodISODateTime", (e, t) => {
	tn.init(e, t), O.init(e, t);
});
function Pi(e) {
	return /* @__PURE__ */ Dr(Ni, e);
}
var Fi = /*@__PURE__*/ s("ZodISODate", (e, t) => {
	nn.init(e, t), O.init(e, t);
});
function Ii(e) {
	return /* @__PURE__ */ Or(Fi, e);
}
var Li = /*@__PURE__*/ s("ZodISOTime", (e, t) => {
	rn.init(e, t), O.init(e, t);
});
function Ri(e) {
	return /* @__PURE__ */ kr(Li, e);
}
var zi = /*@__PURE__*/ s("ZodISODuration", (e, t) => {
	an.init(e, t), O.init(e, t);
});
function Bi(e) {
	return /* @__PURE__ */ Ar(zi, e);
}
var T = /*@__PURE__*/ s("ZodError", (e, t) => {
	Ae.init(e, t), e.name = "ZodError", Object.defineProperties(e, {
		format: { value: (t) => Ne(e, t) },
		flatten: { value: (t) => Me(e, t) },
		addIssue: { value: (t) => {
			e.issues.push(t), e.message = JSON.stringify(e.issues, p, 2);
		} },
		addIssues: { value: (t) => {
			e.issues.push(...t), e.message = JSON.stringify(e.issues, p, 2);
		} },
		isEmpty: { get() {
			return e.issues.length === 0;
		} }
	});
}, { Parent: Error }), Vi = /* @__PURE__ */ Pe(T), Hi = /* @__PURE__ */ Fe(T), Ui = /* @__PURE__ */ Ie(T), Wi = /* @__PURE__ */ Re(T), Gi = /* @__PURE__ */ Be(T), Ki = /* @__PURE__ */ Ve(T), qi = /* @__PURE__ */ He(T), Ji = /* @__PURE__ */ Ue(T), Yi = /* @__PURE__ */ We(T), Xi = /* @__PURE__ */ Ge(T), Zi = /* @__PURE__ */ Ke(T), Qi = /* @__PURE__ */ qe(T), $i = /* @__PURE__ */ new WeakMap();
function ea(e, t, n) {
	let r = Object.getPrototypeOf(e), i = $i.get(r);
	if (i || (i = /* @__PURE__ */ new Set(), $i.set(r, i)), !i.has(t)) {
		i.add(t);
		for (let e in n) {
			let t = n[e];
			Object.defineProperty(r, e, {
				configurable: !0,
				enumerable: !1,
				get() {
					let n = t.bind(this);
					return Object.defineProperty(this, e, {
						configurable: !0,
						writable: !0,
						enumerable: !0,
						value: n
					}), n;
				},
				set(t) {
					Object.defineProperty(this, e, {
						configurable: !0,
						writable: !0,
						enumerable: !0,
						value: t
					});
				}
			});
		}
	}
}
var E = /*@__PURE__*/ s("ZodType", (e, t) => (x.init(e, t), Object.assign(e["~standard"], { jsonSchema: {
	input: ui(e, "input"),
	output: ui(e, "output")
} }), e.toJSONSchema = li(e, {}), e.def = t, e.type = t.type, Object.defineProperty(e, "_def", { value: t }), e.parse = (t, n) => Vi(e, t, n, { callee: e.parse }), e.safeParse = (t, n) => Ui(e, t, n), e.parseAsync = async (t, n) => Hi(e, t, n, { callee: e.parseAsync }), e.safeParseAsync = async (t, n) => Wi(e, t, n), e.spa = e.safeParseAsync, e.encode = (t, n) => Gi(e, t, n), e.decode = (t, n) => Ki(e, t, n), e.encodeAsync = async (t, n) => qi(e, t, n), e.decodeAsync = async (t, n) => Ji(e, t, n), e.safeEncode = (t, n) => Yi(e, t, n), e.safeDecode = (t, n) => Xi(e, t, n), e.safeEncodeAsync = async (t, n) => Zi(e, t, n), e.safeDecodeAsync = async (t, n) => Qi(e, t, n), ea(e, "ZodType", {
	check(...e) {
		let t = this.def;
		return this.clone(g(t, { checks: [...t.checks ?? [], ...e.map((e) => typeof e == "function" ? { _zod: {
			check: e,
			def: { check: "custom" },
			onattach: []
		} } : e)] }), { parent: !0 });
	},
	with(...e) {
		return this.check(...e);
	},
	clone(e, t) {
		return _(this, e, t);
	},
	brand() {
		return this;
	},
	register(e, t) {
		return e.add(this, t), this;
	},
	refine(e, t) {
		return this.check(io(e, t));
	},
	superRefine(e, t) {
		return this.check(ao(e, t));
	},
	overwrite(e) {
		return this.check(/* @__PURE__ */ Xr(e));
	},
	optional() {
		return Ba(this);
	},
	exactOptional() {
		return Ha(this);
	},
	nullable() {
		return Wa(this);
	},
	nullish() {
		return Ba(Wa(this));
	},
	nonoptional(e) {
		return Xa(this, e);
	},
	array() {
		return N(this);
	},
	or(e) {
		return F([this, e]);
	},
	and(e) {
		return I(this, e);
	},
	transform(e) {
		return eo(this, Ra(e));
	},
	default(e) {
		return Ka(this, e);
	},
	prefault(e) {
		return Ja(this, e);
	},
	catch(e) {
		return Qa(this, e);
	},
	pipe(e) {
		return eo(this, e);
	},
	readonly() {
		return no(this);
	},
	describe(e) {
		let t = this.clone();
		return rr.add(t, { description: e }), t;
	},
	meta(...e) {
		if (e.length === 0) return rr.get(this);
		let t = this.clone();
		return rr.add(t, e[0]), t;
	},
	isOptional() {
		return this.safeParse(void 0).success;
	},
	isNullable() {
		return this.safeParse(null).success;
	},
	apply(e) {
		return e(this);
	}
}), Object.defineProperty(e, "description", {
	get() {
		return rr.get(e)?.description;
	},
	configurable: !0
}), e)), ta = /*@__PURE__*/ s("_ZodString", (e, t) => {
	Ut.init(e, t), E.init(e, t), e._zod.processJSONSchema = (t, n, r) => fi(e, t, n, r);
	let n = e._zod.bag;
	e.format = n.format ?? null, e.minLength = n.minimum ?? null, e.maxLength = n.maximum ?? null, ea(e, "_ZodString", {
		regex(...e) {
			return this.check(/* @__PURE__ */ Wr(...e));
		},
		includes(...e) {
			return this.check(/* @__PURE__ */ qr(...e));
		},
		startsWith(...e) {
			return this.check(/* @__PURE__ */ Jr(...e));
		},
		endsWith(...e) {
			return this.check(/* @__PURE__ */ Yr(...e));
		},
		min(...e) {
			return this.check(/* @__PURE__ */ Hr(...e));
		},
		max(...e) {
			return this.check(/* @__PURE__ */ Vr(...e));
		},
		length(...e) {
			return this.check(/* @__PURE__ */ Ur(...e));
		},
		nonempty(...e) {
			return this.check(/* @__PURE__ */ Hr(1, ...e));
		},
		lowercase(e) {
			return this.check(/* @__PURE__ */ Gr(e));
		},
		uppercase(e) {
			return this.check(/* @__PURE__ */ Kr(e));
		},
		trim() {
			return this.check(/* @__PURE__ */ Qr());
		},
		normalize(...e) {
			return this.check(/* @__PURE__ */ Zr(...e));
		},
		toLowerCase() {
			return this.check(/* @__PURE__ */ $r());
		},
		toUpperCase() {
			return this.check(/* @__PURE__ */ ei());
		},
		slugify() {
			return this.check(/* @__PURE__ */ ti());
		}
	});
}), na = /*@__PURE__*/ s("ZodString", (e, t) => {
	Ut.init(e, t), ta.init(e, t), e.email = (t) => e.check(/* @__PURE__ */ ar(ra, t)), e.url = (t) => e.check(/* @__PURE__ */ dr(oa, t)), e.jwt = (t) => e.check(/* @__PURE__ */ Er(Sa, t)), e.emoji = (t) => e.check(/* @__PURE__ */ fr(ca, t)), e.guid = (t) => e.check(/* @__PURE__ */ or(ia, t)), e.uuid = (t) => e.check(/* @__PURE__ */ sr(aa, t)), e.uuidv4 = (t) => e.check(/* @__PURE__ */ cr(aa, t)), e.uuidv6 = (t) => e.check(/* @__PURE__ */ lr(aa, t)), e.uuidv7 = (t) => e.check(/* @__PURE__ */ ur(aa, t)), e.nanoid = (t) => e.check(/* @__PURE__ */ pr(la, t)), e.guid = (t) => e.check(/* @__PURE__ */ or(ia, t)), e.cuid = (t) => e.check(/* @__PURE__ */ mr(ua, t)), e.cuid2 = (t) => e.check(/* @__PURE__ */ hr(da, t)), e.ulid = (t) => e.check(/* @__PURE__ */ gr(fa, t)), e.base64 = (t) => e.check(/* @__PURE__ */ Cr(ya, t)), e.base64url = (t) => e.check(/* @__PURE__ */ wr(ba, t)), e.xid = (t) => e.check(/* @__PURE__ */ _r(pa, t)), e.ksuid = (t) => e.check(/* @__PURE__ */ vr(ma, t)), e.ipv4 = (t) => e.check(/* @__PURE__ */ yr(ha, t)), e.ipv6 = (t) => e.check(/* @__PURE__ */ br(ga, t)), e.cidrv4 = (t) => e.check(/* @__PURE__ */ xr(_a, t)), e.cidrv6 = (t) => e.check(/* @__PURE__ */ Sr(va, t)), e.e164 = (t) => e.check(/* @__PURE__ */ Tr(xa, t)), e.datetime = (t) => e.check(Pi(t)), e.date = (t) => e.check(Ii(t)), e.time = (t) => e.check(Ri(t)), e.duration = (t) => e.check(Bi(t));
});
function D(e) {
	return /* @__PURE__ */ ir(na, e);
}
var O = /*@__PURE__*/ s("ZodStringFormat", (e, t) => {
	S.init(e, t), ta.init(e, t);
}), ra = /*@__PURE__*/ s("ZodEmail", (e, t) => {
	Kt.init(e, t), O.init(e, t);
}), ia = /*@__PURE__*/ s("ZodGUID", (e, t) => {
	Wt.init(e, t), O.init(e, t);
}), aa = /*@__PURE__*/ s("ZodUUID", (e, t) => {
	Gt.init(e, t), O.init(e, t);
}), oa = /*@__PURE__*/ s("ZodURL", (e, t) => {
	qt.init(e, t), O.init(e, t);
});
function sa(e) {
	return /* @__PURE__ */ dr(oa, e);
}
var ca = /*@__PURE__*/ s("ZodEmoji", (e, t) => {
	Jt.init(e, t), O.init(e, t);
}), la = /*@__PURE__*/ s("ZodNanoID", (e, t) => {
	Yt.init(e, t), O.init(e, t);
}), ua = /*@__PURE__*/ s("ZodCUID", (e, t) => {
	Xt.init(e, t), O.init(e, t);
}), da = /*@__PURE__*/ s("ZodCUID2", (e, t) => {
	Zt.init(e, t), O.init(e, t);
}), fa = /*@__PURE__*/ s("ZodULID", (e, t) => {
	Qt.init(e, t), O.init(e, t);
}), pa = /*@__PURE__*/ s("ZodXID", (e, t) => {
	$t.init(e, t), O.init(e, t);
}), ma = /*@__PURE__*/ s("ZodKSUID", (e, t) => {
	en.init(e, t), O.init(e, t);
}), ha = /*@__PURE__*/ s("ZodIPv4", (e, t) => {
	on.init(e, t), O.init(e, t);
}), ga = /*@__PURE__*/ s("ZodIPv6", (e, t) => {
	sn.init(e, t), O.init(e, t);
}), _a = /*@__PURE__*/ s("ZodCIDRv4", (e, t) => {
	cn.init(e, t), O.init(e, t);
}), va = /*@__PURE__*/ s("ZodCIDRv6", (e, t) => {
	ln.init(e, t), O.init(e, t);
}), ya = /*@__PURE__*/ s("ZodBase64", (e, t) => {
	dn.init(e, t), O.init(e, t);
}), ba = /*@__PURE__*/ s("ZodBase64URL", (e, t) => {
	pn.init(e, t), O.init(e, t);
}), xa = /*@__PURE__*/ s("ZodE164", (e, t) => {
	mn.init(e, t), O.init(e, t);
}), Sa = /*@__PURE__*/ s("ZodJWT", (e, t) => {
	gn.init(e, t), O.init(e, t);
}), Ca = /*@__PURE__*/ s("ZodNumber", (e, t) => {
	_n.init(e, t), E.init(e, t), e._zod.processJSONSchema = (t, n, r) => pi(e, t, n, r), ea(e, "ZodNumber", {
		gt(e, t) {
			return this.check(/* @__PURE__ */ Rr(e, t));
		},
		gte(e, t) {
			return this.check(/* @__PURE__ */ zr(e, t));
		},
		min(e, t) {
			return this.check(/* @__PURE__ */ zr(e, t));
		},
		lt(e, t) {
			return this.check(/* @__PURE__ */ Ir(e, t));
		},
		lte(e, t) {
			return this.check(/* @__PURE__ */ Lr(e, t));
		},
		max(e, t) {
			return this.check(/* @__PURE__ */ Lr(e, t));
		},
		int(e) {
			return this.check(A(e));
		},
		safe(e) {
			return this.check(A(e));
		},
		positive(e) {
			return this.check(/* @__PURE__ */ Rr(0, e));
		},
		nonnegative(e) {
			return this.check(/* @__PURE__ */ zr(0, e));
		},
		negative(e) {
			return this.check(/* @__PURE__ */ Ir(0, e));
		},
		nonpositive(e) {
			return this.check(/* @__PURE__ */ Lr(0, e));
		},
		multipleOf(e, t) {
			return this.check(/* @__PURE__ */ Br(e, t));
		},
		step(e, t) {
			return this.check(/* @__PURE__ */ Br(e, t));
		},
		finite() {
			return this;
		}
	});
	let n = e._zod.bag;
	e.minValue = Math.max(n.minimum ?? -Infinity, n.exclusiveMinimum ?? -Infinity) ?? null, e.maxValue = Math.min(n.maximum ?? Infinity, n.exclusiveMaximum ?? Infinity) ?? null, e.isInt = (n.format ?? "").includes("int") || Number.isSafeInteger(n.multipleOf ?? .5), e.isFinite = !0, e.format = n.format ?? null;
});
function k(e) {
	return /* @__PURE__ */ jr(Ca, e);
}
var wa = /*@__PURE__*/ s("ZodNumberFormat", (e, t) => {
	vn.init(e, t), Ca.init(e, t);
});
function A(e) {
	return /* @__PURE__ */ Mr(wa, e);
}
var Ta = /*@__PURE__*/ s("ZodBoolean", (e, t) => {
	yn.init(e, t), E.init(e, t), e._zod.processJSONSchema = (t, n, r) => mi(e, t, n, r);
});
function j(e) {
	return /* @__PURE__ */ Nr(Ta, e);
}
var Ea = /*@__PURE__*/ s("ZodUnknown", (e, t) => {
	bn.init(e, t), E.init(e, t), e._zod.processJSONSchema = (e, t, n) => void 0;
});
function M() {
	return /* @__PURE__ */ Pr(Ea);
}
var Da = /*@__PURE__*/ s("ZodNever", (e, t) => {
	xn.init(e, t), E.init(e, t), e._zod.processJSONSchema = (t, n, r) => hi(e, t, n, r);
});
function Oa(e) {
	return /* @__PURE__ */ Fr(Da, e);
}
var ka = /*@__PURE__*/ s("ZodArray", (e, t) => {
	Cn.init(e, t), E.init(e, t), e._zod.processJSONSchema = (t, n, r) => bi(e, t, n, r), e.element = t.element, ea(e, "ZodArray", {
		min(e, t) {
			return this.check(/* @__PURE__ */ Hr(e, t));
		},
		nonempty(e) {
			return this.check(/* @__PURE__ */ Hr(1, e));
		},
		max(e, t) {
			return this.check(/* @__PURE__ */ Vr(e, t));
		},
		length(e, t) {
			return this.check(/* @__PURE__ */ Ur(e, t));
		},
		unwrap() {
			return this.element;
		}
	});
});
function N(e, t) {
	return /* @__PURE__ */ ni(ka, e, t);
}
var Aa = /*@__PURE__*/ s("ZodObject", (e, t) => {
	On.init(e, t), E.init(e, t), e._zod.processJSONSchema = (t, n, r) => xi(e, t, n, r), m(e, "shape", () => t.shape), ea(e, "ZodObject", {
		keyof() {
			return Fa(Object.keys(this._zod.def.shape));
		},
		catchall(e) {
			return this.clone({
				...this._zod.def,
				catchall: e
			});
		},
		passthrough() {
			return this.clone({
				...this._zod.def,
				catchall: M()
			});
		},
		loose() {
			return this.clone({
				...this._zod.def,
				catchall: M()
			});
		},
		strict() {
			return this.clone({
				...this._zod.def,
				catchall: Oa()
			});
		},
		strip() {
			return this.clone({
				...this._zod.def,
				catchall: void 0
			});
		},
		extend(e) {
			return ve(this, e);
		},
		safeExtend(e) {
			return ye(this, e);
		},
		merge(e) {
			return be(this, e);
		},
		pick(e) {
			return ge(this, e);
		},
		omit(e) {
			return _e(this, e);
		},
		partial(...e) {
			return xe(za, this, e[0]);
		},
		required(...e) {
			return Se(Ya, this, e[0]);
		}
	});
});
function P(e, t) {
	return new Aa({
		type: "object",
		shape: e ?? {},
		...v(t)
	});
}
var ja = /*@__PURE__*/ s("ZodUnion", (e, t) => {
	An.init(e, t), E.init(e, t), e._zod.processJSONSchema = (t, n, r) => Si(e, t, n, r), e.options = t.options;
});
function F(e, t) {
	return new ja({
		type: "union",
		options: e,
		...v(t)
	});
}
var Ma = /*@__PURE__*/ s("ZodIntersection", (e, t) => {
	jn.init(e, t), E.init(e, t), e._zod.processJSONSchema = (t, n, r) => Ci(e, t, n, r);
});
function I(e, t) {
	return new Ma({
		type: "intersection",
		left: e,
		right: t
	});
}
var Na = /*@__PURE__*/ s("ZodRecord", (e, t) => {
	Pn.init(e, t), E.init(e, t), e._zod.processJSONSchema = (t, n, r) => wi(e, t, n, r), e.keyType = t.keyType, e.valueType = t.valueType;
});
function L(e, t, n) {
	return !t || !t._zod ? new Na({
		type: "record",
		keyType: D(),
		valueType: e,
		...v(t)
	}) : new Na({
		type: "record",
		keyType: e,
		valueType: t,
		...v(n)
	});
}
var Pa = /*@__PURE__*/ s("ZodEnum", (e, t) => {
	Fn.init(e, t), E.init(e, t), e._zod.processJSONSchema = (t, n, r) => gi(e, t, n, r), e.enum = t.entries, e.options = Object.values(t.entries);
	let n = new Set(Object.keys(t.entries));
	e.extract = (e, r) => {
		let i = {};
		for (let r of e) if (n.has(r)) i[r] = t.entries[r];
		else throw Error(`Key ${r} not found in enum`);
		return new Pa({
			...t,
			checks: [],
			...v(r),
			entries: i
		});
	}, e.exclude = (e, r) => {
		let i = { ...t.entries };
		for (let t of e) if (n.has(t)) delete i[t];
		else throw Error(`Key ${t} not found in enum`);
		return new Pa({
			...t,
			checks: [],
			...v(r),
			entries: i
		});
	};
});
function Fa(e, t) {
	return new Pa({
		type: "enum",
		entries: Array.isArray(e) ? Object.fromEntries(e.map((e) => [e, e])) : e,
		...v(t)
	});
}
var Ia = /*@__PURE__*/ s("ZodLiteral", (e, t) => {
	In.init(e, t), E.init(e, t), e._zod.processJSONSchema = (t, n, r) => _i(e, t, n, r), e.values = new Set(t.values), Object.defineProperty(e, "value", { get() {
		if (t.values.length > 1) throw Error("This schema contains multiple valid literal values. Use `.values` instead.");
		return t.values[0];
	} });
});
function R(e, t) {
	return new Ia({
		type: "literal",
		values: Array.isArray(e) ? e : [e],
		...v(t)
	});
}
var La = /*@__PURE__*/ s("ZodTransform", (e, t) => {
	Ln.init(e, t), E.init(e, t), e._zod.processJSONSchema = (t, n, r) => yi(e, t, n, r), e._zod.parse = (n, r) => {
		if (r.direction === "backward") throw new l(e.constructor.name);
		n.addIssue = (r) => {
			if (typeof r == "string") n.issues.push(Oe(r, n.value, t));
			else {
				let t = r;
				t.fatal && (t.continue = !1), t.code ??= "custom", t.input ??= n.value, t.inst ??= e, n.issues.push(Oe(t));
			}
		};
		let i = t.transform(n.value, n);
		return i instanceof Promise ? i.then((e) => (n.value = e, n.fallback = !0, n)) : (n.value = i, n.fallback = !0, n);
	};
});
function Ra(e) {
	return new La({
		type: "transform",
		transform: e
	});
}
var za = /*@__PURE__*/ s("ZodOptional", (e, t) => {
	zn.init(e, t), E.init(e, t), e._zod.processJSONSchema = (t, n, r) => Mi(e, t, n, r), e.unwrap = () => e._zod.def.innerType;
});
function Ba(e) {
	return new za({
		type: "optional",
		innerType: e
	});
}
var Va = /*@__PURE__*/ s("ZodExactOptional", (e, t) => {
	Bn.init(e, t), E.init(e, t), e._zod.processJSONSchema = (t, n, r) => Mi(e, t, n, r), e.unwrap = () => e._zod.def.innerType;
});
function Ha(e) {
	return new Va({
		type: "optional",
		innerType: e
	});
}
var Ua = /*@__PURE__*/ s("ZodNullable", (e, t) => {
	Vn.init(e, t), E.init(e, t), e._zod.processJSONSchema = (t, n, r) => Ti(e, t, n, r), e.unwrap = () => e._zod.def.innerType;
});
function Wa(e) {
	return new Ua({
		type: "nullable",
		innerType: e
	});
}
var Ga = /*@__PURE__*/ s("ZodDefault", (e, t) => {
	Hn.init(e, t), E.init(e, t), e._zod.processJSONSchema = (t, n, r) => Di(e, t, n, r), e.unwrap = () => e._zod.def.innerType, e.removeDefault = e.unwrap;
});
function Ka(e, t) {
	return new Ga({
		type: "default",
		innerType: e,
		get defaultValue() {
			return typeof t == "function" ? t() : de(t);
		}
	});
}
var qa = /*@__PURE__*/ s("ZodPrefault", (e, t) => {
	Wn.init(e, t), E.init(e, t), e._zod.processJSONSchema = (t, n, r) => Oi(e, t, n, r), e.unwrap = () => e._zod.def.innerType;
});
function Ja(e, t) {
	return new qa({
		type: "prefault",
		innerType: e,
		get defaultValue() {
			return typeof t == "function" ? t() : de(t);
		}
	});
}
var Ya = /*@__PURE__*/ s("ZodNonOptional", (e, t) => {
	Gn.init(e, t), E.init(e, t), e._zod.processJSONSchema = (t, n, r) => Ei(e, t, n, r), e.unwrap = () => e._zod.def.innerType;
});
function Xa(e, t) {
	return new Ya({
		type: "nonoptional",
		innerType: e,
		...v(t)
	});
}
var Za = /*@__PURE__*/ s("ZodCatch", (e, t) => {
	qn.init(e, t), E.init(e, t), e._zod.processJSONSchema = (t, n, r) => ki(e, t, n, r), e.unwrap = () => e._zod.def.innerType, e.removeCatch = e.unwrap;
});
function Qa(e, t) {
	return new Za({
		type: "catch",
		innerType: e,
		catchValue: typeof t == "function" ? t : () => t
	});
}
var $a = /*@__PURE__*/ s("ZodPipe", (e, t) => {
	Jn.init(e, t), E.init(e, t), e._zod.processJSONSchema = (t, n, r) => Ai(e, t, n, r), e.in = t.in, e.out = t.out;
});
function eo(e, t) {
	return new $a({
		type: "pipe",
		in: e,
		out: t
	});
}
var to = /*@__PURE__*/ s("ZodReadonly", (e, t) => {
	Xn.init(e, t), E.init(e, t), e._zod.processJSONSchema = (t, n, r) => ji(e, t, n, r), e.unwrap = () => e._zod.def.innerType;
});
function no(e) {
	return new to({
		type: "readonly",
		innerType: e
	});
}
var ro = /*@__PURE__*/ s("ZodCustom", (e, t) => {
	Qn.init(e, t), E.init(e, t), e._zod.processJSONSchema = (t, n, r) => vi(e, t, n, r);
});
function io(e, t = {}) {
	return /* @__PURE__ */ ri(ro, e, t);
}
function ao(e, t) {
	return /* @__PURE__ */ ii(e, t);
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/schema-deserialize.js
var oo = Symbol("skippedItem");
function z(e, t) {
	return e.catch(t);
}
function B(e, t) {
	let n = e.catch(t);
	return M().transform((e, t) => e === void 0 ? (t.addIssue({
		code: "custom",
		message: "Required value is missing"
	}), o) : n.parse(e));
}
function so(e, t) {
	if (typeof e != "object" || !e || Array.isArray(e)) return;
	let n = e[t];
	return typeof n == "string" ? n : void 0;
}
function co(e, t, n) {
	return e.superRefine((e, r) => {
		let i = so(e, t);
		i !== void 0 && n.includes(i) && r.addIssue({
			code: "custom",
			path: [t],
			message: `${t} ${JSON.stringify(i)} is reserved by a known variant, but the value does not match that variant's schema`
		});
	});
}
function lo(e, t, n) {
	return M().transform((r, i) => {
		let a = e.safeParse(r);
		if (!a.success) {
			for (let e of a.error.issues) i.addIssue({
				...e,
				input: r
			});
			return o;
		}
		let s = a.data, c = so(r, t);
		if (c !== void 0 && !n.includes(c)) {
			let e = r;
			for (let [t, n] of Object.entries(e)) t !== "__proto__" && (Object.hasOwn(s, t) || (s[t] = n));
		}
		return s;
	});
}
function V(e) {
	return N(e.catch(oo)).transform((e) => e.filter((e) => e !== oo));
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/schema/zod.gen.js
var H = F([k(), D()]).nullable(), U = D(), uo = P({
	sessionId: U,
	path: D(),
	content: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), fo = P({
	sessionId: U,
	path: D(),
	line: z(A().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	limit: z(A().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), po = D(), mo = F([
	R("read"),
	R("edit"),
	R("delete"),
	R("move"),
	R("search"),
	R("execute"),
	R("think"),
	R("fetch"),
	R("switch_mode"),
	R("other")
]), ho = F([
	R("pending"),
	R("in_progress"),
	R("completed"),
	R("failed")
]), go = P({
	audience: z(V(F([R("assistant"), R("user")])).nullish(), () => void 0),
	lastModified: z(D().nullish(), () => void 0),
	priority: z(k().nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), _o = P({
	annotations: z(go.nullish(), () => void 0),
	text: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), vo = P({
	annotations: z(go.nullish(), () => void 0),
	data: D(),
	mimeType: D(),
	uri: z(D().nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), yo = P({
	annotations: z(go.nullish(), () => void 0),
	data: D(),
	mimeType: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), bo = P({
	annotations: z(go.nullish(), () => void 0),
	description: z(D().nullish(), () => void 0),
	mimeType: z(D().nullish(), () => void 0),
	name: D(),
	size: z(k().nullish(), () => void 0),
	title: z(D().nullish(), () => void 0),
	uri: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), xo = F([P({
	mimeType: z(D().nullish(), () => void 0),
	text: D(),
	uri: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), P({
	blob: D(),
	mimeType: z(D().nullish(), () => void 0),
	uri: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
})]), So = P({
	annotations: z(go.nullish(), () => void 0),
	resource: xo,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Co = F([
	_o.and(P({ type: R("text") })),
	vo.and(P({ type: R("image") })),
	yo.and(P({ type: R("audio") })),
	bo.and(P({ type: R("resource_link") })),
	So.and(P({ type: R("resource") }))
]), wo = P({
	content: Co,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), To = P({
	path: D(),
	oldText: z(D().nullish(), () => void 0),
	newText: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Eo = D(), Do = P({
	terminalId: Eo,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Oo = F([
	wo.and(P({ type: R("content") })),
	To.and(P({ type: R("diff") })),
	Do.and(P({ type: R("terminal") }))
]), ko = P({
	path: D(),
	line: z(A().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Ao = P({
	toolCallId: po,
	kind: z(mo.nullish(), () => void 0),
	status: z(ho.nullish(), () => void 0),
	title: z(D().nullish(), () => void 0),
	name: z(D().nullish(), () => void 0),
	content: z(V(Oo).nullish(), () => void 0),
	locations: z(V(ko).nullish(), () => void 0),
	rawInput: z(M().optional(), () => void 0),
	rawOutput: z(M().optional(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), jo = D(), Mo = F([
	R("allow_once"),
	R("allow_always"),
	R("reject_once"),
	R("reject_always")
]), No = P({
	sessionId: U,
	toolCall: Ao,
	options: N(P({
		optionId: jo,
		name: D(),
		kind: Mo,
		_meta: z(L(D(), M()).nullish(), () => void 0)
	})),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Po = P({
	name: D(),
	value: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Fo = P({
	sessionId: U,
	command: D(),
	args: z(V(D()).optional(), () => []),
	env: z(V(Po).optional(), () => []),
	cwd: z(D().nullish(), () => void 0),
	outputByteLimit: z(k().nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Io = P({
	sessionId: U,
	terminalId: Eo,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Lo = P({
	sessionId: U,
	terminalId: Eo,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Ro = P({
	sessionId: U,
	terminalId: Eo,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), zo = P({
	sessionId: U,
	terminalId: Eo,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Bo = P({
	sessionId: U,
	toolCallId: z(po.nullish(), () => void 0)
}), Vo = P({ requestId: H }), Ho = R("object"), Uo = F([
	R("email"),
	R("uri"),
	R("date"),
	R("date-time")
]), Wo = P({
	const: D(),
	title: D(),
	description: z(D().nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Go = P({
	title: z(D().nullish(), () => void 0),
	description: z(D().nullish(), () => void 0),
	minLength: A().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(),
	maxLength: A().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(),
	pattern: D().nullish(),
	format: Uo.nullish(),
	default: z(D().nullish(), () => void 0),
	enum: N(D()).nullish(),
	oneOf: N(Wo).nullish(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Ko = P({
	title: z(D().nullish(), () => void 0),
	description: z(D().nullish(), () => void 0),
	minimum: k().nullish(),
	maximum: k().nullish(),
	default: z(k().nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), qo = P({
	title: z(D().nullish(), () => void 0),
	description: z(D().nullish(), () => void 0),
	minimum: k().nullish(),
	maximum: k().nullish(),
	default: z(k().nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Jo = P({
	title: z(D().nullish(), () => void 0),
	description: z(D().nullish(), () => void 0),
	default: z(j().nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Yo = P({
	enum: N(D()),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Xo = P({
	anyOf: N(Wo),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Zo = lo(F([
	Yo.and(P({ type: R("string") })),
	co(P({ type: D() }), "type", ["string"]),
	Xo
]), "type", ["string"]), Qo = P({
	title: z(D().nullish(), () => void 0),
	description: z(D().nullish(), () => void 0),
	minItems: k().nullish(),
	maxItems: k().nullish(),
	items: Zo,
	default: z(V(D()).nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), $o = lo(F([
	Go.and(P({ type: R("string") })),
	Ko.and(P({ type: R("number") })),
	qo.and(P({ type: R("integer") })),
	Jo.and(P({ type: R("boolean") })),
	Qo.and(P({ type: R("array") })),
	co(P({ type: D() }), "type", [
		"array",
		"boolean",
		"integer",
		"number",
		"string"
	])
]), "type", [
	"array",
	"boolean",
	"integer",
	"number",
	"string"
]), es = P({
	type: z(Ho.optional().default("object"), () => "object"),
	title: z(D().nullish(), () => void 0),
	properties: L(D(), $o).optional().default({}),
	required: N(D()).nullish(),
	description: z(D().nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), ts = I(F([Bo, Vo]), P({ requestedSchema: es })), ns = D(), rs = I(F([Bo, Vo]), P({
	elicitationId: ns,
	url: sa()
})), is = lo(I(F([
	ts.and(P({ mode: R("form") })),
	rs.and(P({ mode: R("url") })),
	co(I(F([Bo, Vo]), P({ mode: D() })), "mode", ["form", "url"])
]), P({
	message: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
})), "mode", ["form", "url"]), as = D(), os = P({
	serverId: as,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), ss = D(), cs = P({
	connectionId: ss,
	method: D(),
	params: L(D(), M()).nullish(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), ls = P({
	connectionId: ss,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), us = M();
P({
	id: H,
	method: D(),
	params: F([
		uo,
		fo,
		No,
		Fo,
		Io,
		Lo,
		Ro,
		zo,
		is,
		os,
		cs,
		ls,
		us
	]).nullish()
});
var ds = A().gte(0).lte(65535), fs = P({
	image: z(j().optional().default(!1), () => !1),
	audio: z(j().optional().default(!1), () => !1),
	embeddedContext: z(j().optional().default(!1), () => !1),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), ps = P({
	http: z(j().optional().default(!1), () => !1),
	sse: z(j().optional().default(!1), () => !1),
	acp: z(j().optional().default(!1), () => !1),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), ms = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), hs = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), gs = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), _s = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), vs = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), ys = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), bs = P({
	list: z(ms.nullish(), () => void 0),
	delete: z(hs.nullish(), () => void 0),
	additionalDirectories: z(gs.nullish(), () => void 0),
	fork: z(_s.nullish(), () => void 0),
	resume: z(vs.nullish(), () => void 0),
	close: z(ys.nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), xs = P({
	logout: z(P({ _meta: z(L(D(), M()).nullish(), () => void 0) }).nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Ss = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), Cs = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), ws = P({
	syncKind: F([R("full"), R("incremental")]),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Ts = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), Es = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), Ds = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), Os = P({
	document: z(P({
		didOpen: z(Cs.nullish(), () => void 0),
		didChange: z(ws.nullish(), () => void 0),
		didClose: z(Ts.nullish(), () => void 0),
		didSave: z(Es.nullish(), () => void 0),
		didFocus: z(Ds.nullish(), () => void 0),
		_meta: z(L(D(), M()).nullish(), () => void 0)
	}).nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), ks = P({
	maxCount: z(A().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), As = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), js = P({
	maxCount: z(A().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Ms = P({
	maxCount: z(A().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Ns = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), Ps = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), Fs = P({
	recentFiles: z(ks.nullish(), () => void 0),
	relatedSnippets: z(As.nullish(), () => void 0),
	editHistory: z(js.nullish(), () => void 0),
	userActions: z(Ms.nullish(), () => void 0),
	openFiles: z(Ns.nullish(), () => void 0),
	diagnostics: z(Ps.nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Is = P({
	events: z(Os.nullish(), () => void 0),
	context: z(Fs.nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Ls = F([
	R("utf-16"),
	R("utf-32"),
	R("utf-8")
]), Rs = P({
	loadSession: z(j().optional().default(!1), () => !1),
	promptCapabilities: z(fs.optional().default({
		image: !1,
		audio: !1,
		embeddedContext: !1
	}), () => ({
		image: !1,
		audio: !1,
		embeddedContext: !1
	})),
	mcpCapabilities: z(ps.optional().default({
		http: !1,
		sse: !1,
		acp: !1
	}), () => ({
		http: !1,
		sse: !1,
		acp: !1
	})),
	sessionCapabilities: z(bs.optional().default({}), () => ({})),
	auth: z(xs.optional().default({}), () => ({})),
	providers: z(Ss.nullish(), () => void 0),
	nes: z(Is.nullish(), () => void 0),
	positionEncoding: z(Ls.nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), zs = D(), Bs = P({
	id: zs,
	name: D(),
	description: z(D().nullish(), () => void 0),
	args: z(V(D()).optional(), () => []),
	env: z(L(D(), D()).optional(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Vs = P({
	id: zs,
	name: D(),
	description: z(D().nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Hs = F([Bs.and(P({ type: R("terminal") })), Vs]), Us = P({
	name: D(),
	title: z(D().nullish(), () => void 0),
	version: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Ws = P({
	protocolVersion: ds,
	agentCapabilities: z(Rs.optional().default({
		loadSession: !1,
		promptCapabilities: {
			image: !1,
			audio: !1,
			embeddedContext: !1
		},
		mcpCapabilities: {
			http: !1,
			sse: !1,
			acp: !1
		},
		sessionCapabilities: {},
		auth: {}
	}), () => ({
		loadSession: !1,
		promptCapabilities: {
			image: !1,
			audio: !1,
			embeddedContext: !1
		},
		mcpCapabilities: {
			http: !1,
			sse: !1,
			acp: !1
		},
		sessionCapabilities: {},
		auth: {}
	})),
	authMethods: z(V(Hs).optional().default([]), () => []),
	agentInfo: z(Us.nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Gs = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), Ks = D(), qs = F([
	R("anthropic"),
	R("openai"),
	R("azure"),
	R("vertex"),
	R("bedrock"),
	D()
]), Js = P({
	apiType: qs,
	baseUrl: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Ys = P({
	providers: N(P({
		providerId: Ks,
		supported: B(V(qs), () => []),
		required: j(),
		current: Js.nullish(),
		_meta: z(L(D(), M()).nullish(), () => void 0)
	})),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Xs = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), Zs = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), Qs = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), $s = D(), ec = P({
	currentModeId: $s,
	availableModes: B(V(P({
		id: $s,
		name: D(),
		description: z(D().nullish(), () => void 0),
		_meta: z(L(D(), M()).nullish(), () => void 0)
	})), () => []),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), tc = D(), nc = F([
	R("mode"),
	R("model"),
	R("model_config"),
	R("thought_level"),
	D()
]), rc = D(), ic = P({
	value: rc,
	name: D(),
	description: z(D().nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), ac = P({
	group: D(),
	name: D(),
	options: B(V(ic), () => []),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), oc = P({
	currentValue: rc,
	options: F([N(ic), N(ac)])
}), sc = P({ currentValue: j() }), cc = I(F([oc.and(P({ type: R("select") })), sc.and(P({ type: R("boolean") }))]), P({
	id: tc,
	name: D(),
	description: z(D().nullish(), () => void 0),
	category: z(nc.nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
})), lc = P({
	sessionId: U,
	modes: z(ec.nullish(), () => void 0),
	configOptions: z(V(cc).nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), uc = P({
	modes: z(ec.nullish(), () => void 0),
	configOptions: z(V(cc).nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), dc = P({
	sessions: B(V(P({
		sessionId: U,
		cwd: D(),
		additionalDirectories: z(V(D()).optional(), () => []),
		title: z(D().nullish(), () => void 0),
		updatedAt: z(D().nullish(), () => void 0),
		_meta: z(L(D(), M()).nullish(), () => void 0)
	})), () => []),
	nextCursor: z(D().nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), fc = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), pc = P({
	sessionId: U,
	modes: z(ec.nullish(), () => void 0),
	configOptions: z(V(cc).nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), mc = P({
	modes: z(ec.nullish(), () => void 0),
	configOptions: z(V(cc).nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), hc = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), gc = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), _c = P({
	configOptions: B(V(cc), () => []),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), vc = P({
	stopReason: F([
		R("end_turn"),
		R("max_tokens"),
		R("max_turn_requests"),
		R("refusal"),
		R("cancelled")
	]),
	usage: z(P({
		totalTokens: k(),
		inputTokens: k(),
		outputTokens: k(),
		thoughtTokens: z(k().nullish(), () => void 0),
		cachedReadTokens: z(k().nullish(), () => void 0),
		cachedWriteTokens: z(k().nullish(), () => void 0),
		_meta: z(L(D(), M()).nullish(), () => void 0)
	}).nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), yc = P({
	sessionId: U,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), bc = D(), W = P({
	line: A().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }),
	character: A().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), xc = P({
	start: W,
	end: W,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Sc = P({
	range: xc,
	newText: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Cc = P({
	id: bc,
	uri: D(),
	edits: N(Sc),
	cursorPosition: z(W.nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), wc = P({
	id: bc,
	uri: D(),
	position: W,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Tc = P({
	id: bc,
	uri: D(),
	position: W,
	newName: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Ec = P({
	id: bc,
	uri: D(),
	search: D(),
	replace: D(),
	isRegex: j().nullish(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Dc = P({
	suggestions: N(F([
		Cc.and(P({ kind: R("edit") })),
		wc.and(P({ kind: R("jump") })),
		Tc.and(P({ kind: R("rename") })),
		Ec.and(P({ kind: R("searchAndReplace") }))
	])),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Oc = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), kc = M(), Ac = M(), jc = P({
	code: F([
		R(-32700),
		R(-32600),
		R(-32601),
		R(-32602),
		R(-32603),
		R(-32800),
		R(-32e3),
		R(-32002),
		A().min(-2147483648, { error: "Invalid value: Expected int32 to be >= -2147483648" }).max(2147483647, { error: "Invalid value: Expected int32 to be <= 2147483647" })
	]),
	message: D(),
	data: z(M().optional(), () => void 0)
});
F([P({
	id: H,
	result: F([
		Ws,
		Gs,
		Ys,
		Xs,
		Zs,
		Qs,
		lc,
		uc,
		dc,
		fc,
		pc,
		mc,
		hc,
		gc,
		_c,
		vc,
		yc,
		Dc,
		Oc,
		kc,
		Ac
	])
}), P({
	id: H,
	error: jc
})]);
var Mc = P({
	content: Co,
	messageId: z(D().nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Nc = P({
	toolCallId: po,
	title: D(),
	name: z(D().nullish(), () => void 0),
	kind: z(mo.optional(), () => void 0),
	status: z(ho.optional(), () => void 0),
	content: z(V(Oo).optional(), () => []),
	locations: z(V(ko).optional(), () => []),
	rawInput: z(M().optional(), () => void 0),
	rawOutput: z(M().optional(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Pc = F([
	R("high"),
	R("medium"),
	R("low")
]), Fc = F([
	R("pending"),
	R("in_progress"),
	R("completed")
]), Ic = P({
	content: D(),
	priority: Pc,
	status: Fc,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Lc = P({
	entries: B(V(Ic), () => []),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Rc = D(), zc = P({
	planId: Rc,
	entries: B(V(Ic), () => []),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Bc = P({
	planId: Rc,
	uri: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Vc = P({
	planId: Rc,
	content: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Hc = P({
	plan: F([
		zc.and(P({ type: R("items") })),
		Bc.and(P({ type: R("file") })),
		Vc.and(P({ type: R("markdown") }))
	]),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Uc = P({
	planId: Rc,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Wc = P({
	hint: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Gc = P({
	availableCommands: B(V(P({
		name: D(),
		description: D(),
		input: z(Wc.nullish(), () => void 0),
		_meta: z(L(D(), M()).nullish(), () => void 0)
	})), () => []),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Kc = P({
	currentModeId: $s,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), qc = P({
	configOptions: B(V(cc), () => []),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Jc = P({
	title: z(D().nullish(), () => void 0),
	updatedAt: z(D().nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Yc = P({
	amount: k(),
	currency: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Xc = P({
	used: k(),
	size: k(),
	cost: z(Yc.nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Zc = D(), Qc = P({
	compactionId: Zc,
	status: F([
		R("in_progress"),
		R("completed"),
		R("failed"),
		R("cancelled"),
		D()
	]),
	summary: z(V(Co).nullish(), () => void 0),
	error: z(D().nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), $c = P({
	compactionId: Zc,
	content: Co,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), el = P({
	sessionId: U,
	update: F([
		Mc.and(P({ sessionUpdate: R("user_message_chunk") })),
		Mc.and(P({ sessionUpdate: R("agent_message_chunk") })),
		Mc.and(P({ sessionUpdate: R("agent_thought_chunk") })),
		Nc.and(P({ sessionUpdate: R("tool_call") })),
		Ao.and(P({ sessionUpdate: R("tool_call_update") })),
		Lc.and(P({ sessionUpdate: R("plan") })),
		Hc.and(P({ sessionUpdate: R("plan_update") })),
		Uc.and(P({ sessionUpdate: R("plan_removed") })),
		Gc.and(P({ sessionUpdate: R("available_commands_update") })),
		Kc.and(P({ sessionUpdate: R("current_mode_update") })),
		qc.and(P({ sessionUpdate: R("config_option_update") })),
		Jc.and(P({ sessionUpdate: R("session_info_update") })),
		Xc.and(P({ sessionUpdate: R("usage_update") })),
		Qc.and(P({ sessionUpdate: R("compaction_update") })),
		$c.and(P({ sessionUpdate: R("compaction_summary_chunk") }))
	]),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), tl = P({
	elicitationId: ns,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), nl = P({
	connectionId: ss,
	method: D(),
	params: z(L(D(), M()).nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), rl = M();
P({
	method: D(),
	params: F([
		el,
		tl,
		nl,
		rl
	]).nullish()
});
var il = P({
	readTextFile: z(j().optional().default(!1), () => !1),
	writeTextFile: z(j().optional().default(!1), () => !1),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), al = L(D(), M()), ol = P({
	boolean: z(P({ _meta: z(L(D(), M()).nullish(), () => void 0) }).nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), sl = P({
	compaction: z(al.nullish(), () => void 0),
	configOptions: z(ol.nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), cl = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), ll = P({
	terminal: z(j().optional().default(!1), () => !1),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), ul = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), dl = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), fl = P({
	form: z(ul.nullish(), () => void 0),
	url: z(dl.nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), pl = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), ml = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), hl = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), gl = P({
	jump: z(pl.nullish(), () => void 0),
	rename: z(ml.nullish(), () => void 0),
	searchAndReplace: z(hl.nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), _l = P({
	protocolVersion: ds,
	clientCapabilities: z(P({
		fs: z(il.optional().default({
			readTextFile: !1,
			writeTextFile: !1
		}), () => ({
			readTextFile: !1,
			writeTextFile: !1
		})),
		terminal: z(j().optional().default(!1), () => !1),
		session: z(sl.nullish(), () => void 0),
		plan: z(cl.nullish(), () => void 0),
		auth: z(ll.optional().default({ terminal: !1 }), () => ({ terminal: !1 })),
		elicitation: z(fl.nullish(), () => void 0),
		nes: z(gl.nullish(), () => void 0),
		positionEncodings: z(V(Ls).optional(), () => []),
		_meta: z(L(D(), M()).nullish(), () => void 0)
	}).optional().default({
		fs: {
			readTextFile: !1,
			writeTextFile: !1
		},
		terminal: !1,
		auth: { terminal: !1 }
	}), () => ({
		fs: {
			readTextFile: !1,
			writeTextFile: !1
		},
		terminal: !1,
		auth: { terminal: !1 }
	})),
	clientInfo: z(Us.nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), vl = P({
	methodId: zs,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), yl = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), bl = P({
	providerId: Ks,
	apiType: qs,
	baseUrl: D(),
	headers: L(D(), D()).optional(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), xl = P({
	providerId: Ks,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Sl = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), Cl = P({
	name: D(),
	value: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), wl = P({
	name: D(),
	url: D(),
	headers: N(Cl),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Tl = P({
	name: D(),
	url: D(),
	headers: N(Cl),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), El = P({
	name: D(),
	serverId: as,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Dl = P({
	name: D(),
	command: D(),
	args: N(D()),
	env: N(Po),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Ol = F([
	wl.and(P({ type: R("http") })),
	Tl.and(P({ type: R("sse") })),
	El.and(P({ type: R("acp") })),
	Dl
]), kl = P({
	cwd: D(),
	additionalDirectories: z(V(D()).optional(), () => []),
	mcpServers: B(V(Ol), () => []),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Al = P({
	mcpServers: B(V(Ol), () => []),
	cwd: D(),
	additionalDirectories: z(V(D()).optional(), () => []),
	sessionId: U,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), jl = P({
	cwd: D().nullish(),
	cursor: D().nullish(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Ml = P({
	sessionId: U,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Nl = P({
	sessionId: U,
	cwd: D(),
	additionalDirectories: z(V(D()).optional(), () => []),
	mcpServers: z(V(Ol).optional(), () => []),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Pl = P({
	sessionId: U,
	cwd: D(),
	additionalDirectories: z(V(D()).optional(), () => []),
	mcpServers: z(V(Ol).optional(), () => []),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Fl = P({
	sessionId: U,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Il = P({
	sessionId: U,
	modeId: $s,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Ll = I(F([P({
	value: j(),
	type: R("boolean")
}), P({ value: rc })]), P({
	sessionId: U,
	configId: tc,
	_meta: z(L(D(), M()).nullish(), () => void 0)
})), Rl = P({
	sessionId: U,
	prompt: N(Co),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), zl = P({
	uri: D(),
	name: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Bl = P({
	name: D(),
	owner: D(),
	remoteUrl: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Vl = P({
	workspaceUri: z(D().nullish(), () => void 0),
	workspaceFolders: N(zl).nullish(),
	repository: z(Bl.nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Hl = F([
	R("automatic"),
	R("diagnostic"),
	R("manual")
]), Ul = P({
	uri: D(),
	languageId: D(),
	text: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Wl = P({
	startLine: A().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }),
	endLine: A().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }),
	text: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Gl = P({
	uri: D(),
	excerpts: N(Wl),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Kl = P({
	uri: D(),
	diff: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), ql = P({
	action: D(),
	uri: D(),
	position: W,
	timestampMs: k(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Jl = P({
	uri: D(),
	languageId: D(),
	visibleRange: z(xc.nullish(), () => void 0),
	lastFocusedMs: z(k().nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Yl = F([
	R("error"),
	R("warning"),
	R("information"),
	R("hint")
]), Xl = P({
	uri: D(),
	range: xc,
	severity: Yl,
	message: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Zl = P({
	recentFiles: N(Ul).nullish(),
	relatedSnippets: N(Gl).nullish(),
	editHistory: N(Kl).nullish(),
	userActions: N(ql).nullish(),
	openFiles: N(Jl).nullish(),
	diagnostics: N(Xl).nullish(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), Ql = P({
	sessionId: U,
	uri: D(),
	version: k(),
	position: W,
	selection: xc.nullish(),
	triggerKind: Hl,
	context: Zl.nullish(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), $l = P({
	sessionId: U,
	_meta: z(L(D(), M()).nullish(), () => void 0)
});
P({
	id: H,
	method: D(),
	params: F([
		_l,
		vl,
		yl,
		bl,
		xl,
		Sl,
		kl,
		Al,
		jl,
		Ml,
		Nl,
		Pl,
		Fl,
		Il,
		Ll,
		Rl,
		Vl,
		Ql,
		$l,
		cs,
		us
	]).nullish()
});
var eu = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), tu = P({
	content: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), nu = P({
	optionId: jo,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), ru = P({
	outcome: F([P({ outcome: R("cancelled") }), nu.and(P({ outcome: R("selected") }))]),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), iu = P({
	terminalId: Eo,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), au = P({
	exitCode: z(A().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	signal: z(D().nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), ou = P({
	output: D(),
	truncated: j(),
	exitStatus: z(au.nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), su = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), cu = P({
	exitCode: z(A().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	signal: z(D().nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), lu = P({ _meta: z(L(D(), M()).nullish(), () => void 0) }), uu = F([
	D(),
	k(),
	k(),
	j(),
	N(D())
]), du = P({ content: L(D(), uu).nullish() });
F([P({
	id: H,
	result: F([
		eu,
		tu,
		ru,
		iu,
		ou,
		su,
		cu,
		lu,
		lo(I(F([
			du.and(P({ action: R("accept") })),
			P({ action: R("decline") }),
			P({ action: R("cancel") }),
			co(P({ action: D() }), "action", [
				"accept",
				"cancel",
				"decline"
			])
		]), P({ _meta: z(L(D(), M()).nullish(), () => void 0) })), "action", [
			"accept",
			"cancel",
			"decline"
		]),
		P({
			connectionId: ss,
			_meta: z(L(D(), M()).nullish(), () => void 0)
		}),
		P({ _meta: z(L(D(), M()).nullish(), () => void 0) }),
		Ac,
		kc
	])
}), P({
	id: H,
	error: jc
})]);
var fu = P({
	sessionId: U,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), pu = P({
	sessionId: U,
	uri: D(),
	languageId: D(),
	version: k(),
	text: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), mu = P({
	range: xc.nullish(),
	text: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), hu = P({
	sessionId: U,
	uri: D(),
	version: k(),
	contentChanges: B(V(mu), () => []),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), gu = P({
	sessionId: U,
	uri: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), _u = P({
	sessionId: U,
	uri: D(),
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), vu = P({
	sessionId: U,
	uri: D(),
	version: k(),
	position: W,
	visibleRange: xc,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), yu = P({
	sessionId: U,
	id: bc,
	_meta: z(L(D(), M()).nullish(), () => void 0)
}), bu = P({
	sessionId: U,
	id: bc,
	reason: z(F([
		R("rejected"),
		R("ignored"),
		R("replaced"),
		R("cancelled")
	]).nullish(), () => void 0),
	_meta: z(L(D(), M()).nullish(), () => void 0)
});
P({
	method: D(),
	params: F([
		fu,
		pu,
		hu,
		gu,
		_u,
		vu,
		yu,
		bu,
		nl,
		rl
	]).nullish()
}), P({
	requestId: H,
	_meta: z(L(D(), M()).nullish(), () => void 0)
});
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/jsonrpc.js
var xu = "$/cancel_request";
function Su(e) {
	return Eu(e) && "id" in e && typeof e.method == "string" && Du(e.id);
}
function Cu(e) {
	if (!Eu(e) || "method" in e || !("id" in e) || !Du(e.id)) return !1;
	let t = Object.hasOwn(e, "result"), n = Object.hasOwn(e, "error");
	return t === n ? !1 : !n || ju(e.error);
}
function wu(e) {
	return Eu(e) && !("id" in e) && typeof e.method == "string";
}
function Tu(e) {
	return typeof e == "object" && !!e;
}
function Eu(e) {
	return Tu(e) && e.jsonrpc === "2.0";
}
function Du(e) {
	return e === null || typeof e == "string" || typeof e == "number" && Number.isFinite(e);
}
function Ou(e) {
	return Tu(e) && !("method" in e) && ("id" in e || "result" in e || "error" in e);
}
function ku(e) {
	let t = !1, n = !1, r = !1, i = !1;
	for (let a of e) t ||= Su(a) || wu(a), n ||= Cu(a), Tu(a) && (r ||= "method" in a, i ||= "result" in a || "error" in a);
	return t ? !1 : n ? !0 : i && !r;
}
function Au(e) {
	if (!(!Tu(e) || !Du(e.requestId))) return e.requestId;
}
function ju(e) {
	return Tu(e) && typeof e.code == "number" && Number.isInteger(e.code) && typeof e.message == "string";
}
var G = {
	yes() {
		return { handled: !0 };
	},
	no(e, t = !1) {
		return {
			handled: !1,
			message: e,
			retry: t
		};
	}
};
function Mu(e) {
	let t = Promise.reject(e);
	return t.catch(() => {}), t;
}
function Nu(e) {
	if (e instanceof Error || typeof e == "object" && e && "message" in e && typeof e.message == "string") return e.message;
}
function Pu(e) {
	return typeof e == "object" && !!e && "name" in e && e.name === "ZodError" && "issues" in e && Array.isArray(e.issues) && "format" in e && typeof e.format == "function";
}
function Fu(e) {
	if (e instanceof K) return e.toResult();
	if (Pu(e)) return K.invalidParams(e.format()).toResult();
	let t = Nu(e);
	try {
		return K.internalError(t ? JSON.parse(t) : {}).toResult();
	} catch {
		return K.internalError({ details: t }).toResult();
	}
}
function Iu(e) {
	return e instanceof K && e.code === -32800 ? e : K.requestCancelled(e);
}
function Lu(e, t) {
	let n = Ru(e, t);
	return n ? n.toResult() : Fu(e);
}
function Ru(e, t) {
	if (!(!t.aborted || !zu(e))) return Iu(t.reason);
}
function zu(e) {
	if (typeof e != "object" || !e) return !1;
	let t = e;
	return t.name === "AbortError" || t.code === "ABORT_ERR";
}
var Bu = class {
	id;
	sendResult;
	signal;
	finishRequest;
	didRespond = !1;
	constructor(e, t, n = new AbortController().signal, r) {
		this.id = e, this.sendResult = t, this.signal = n, this.finishRequest = r;
	}
	get responded() {
		return this.didRespond;
	}
	respond(e) {
		return this.respondWithResult({ result: e ?? null });
	}
	respondWithError(e) {
		let t = e instanceof K ? e.toErrorResponse() : e;
		return this.respondWithResult({ error: t });
	}
	respondWithResult(e) {
		return this.didRespond ? Mu(/* @__PURE__ */ Error("JSON-RPC request already responded")) : (this.didRespond = !0, this.sendResult(e).finally(() => {
			this.finishRequest?.();
		}));
	}
}, Vu = /* @__PURE__ */ new WeakMap(), Hu = class {
	disposeHandler;
	active = !0;
	constructor(e) {
		this.disposeHandler = e;
	}
	dispose() {
		this.active && (this.active = !1, this.disposeHandler());
	}
	[Symbol.dispose]() {
		this.dispose();
	}
	runIndefinitely() {
		return this;
	}
}, Uu = class {
	connection;
	constructor(e) {
		this.connection = e;
	}
	sendRequest(e, t, n, r) {
		return this.connection.sendRequest(e, t, n, r);
	}
	sendNotification(e, t) {
		return this.connection.sendNotification(e, t);
	}
	sendBatch(e) {
		return this.connection.sendBatch(e);
	}
	sendCancelRequest(e) {
		return this.connection.sendCancelRequest(e);
	}
	addDynamicHandler(e) {
		return this.connection.addDynamicHandler(e);
	}
	get signal() {
		return this.connection.signal;
	}
	get closed() {
		return this.connection.closed;
	}
}, Wu = class {
	pendingResponses = /* @__PURE__ */ new Map();
	incomingRequests = /* @__PURE__ */ new Map();
	nextRequestId = 0;
	staticHandlers = [];
	dynamicHandlers = /* @__PURE__ */ new Set();
	stream;
	writeQueue = Promise.resolve();
	abortController = new AbortController();
	closedPromise;
	retryQueue = [];
	context = new Uu(this);
	receiveReader;
	allowBatches = !0;
	constructor(e, t, n, r) {
		if (typeof e == "function") {
			let i = e, a = t, o = n;
			this.initialize(o, [...r?.handlers ?? [], this.legacyHandler(i, a)], r);
			return;
		}
		let i = e, a = t, o = n;
		this.initialize(i, [...o?.handlers ?? [], ...a], o);
	}
	static builder() {
		return new Gu();
	}
	runUntil(e) {
		let t = !1, n = Promise.resolve().then(() => e(this.context)).finally(() => {
			t = !0;
		}), r = this.closed.then(() => {
			if (t) return new Promise(() => {});
			throw this.closedReason();
		});
		return Promise.race([n, r]).finally(() => {
			t = !0, this.close();
		});
	}
	addDynamicHandler(e) {
		if (this.dynamicHandlers.add(e), this.retryQueue.length > 0) for (let e of this.retryQueue.splice(0)) this.processIncomingMessage(e).catch((e) => this.close(e));
		return new Hu(() => {
			this.dynamicHandlers.delete(e);
		});
	}
	get signal() {
		return this.abortController.signal;
	}
	get closed() {
		return this.closedPromise;
	}
	getContext() {
		return this.context;
	}
	sendRequest(e, t, n, r = {}) {
		if (this.abortController.signal.aborted) return Mu(this.closedReason());
		let i = this.prepareRequest(e, t, n, r);
		return this.sendWireMessage(i.message).catch(() => {}), r.cancellationSignal?.aborted && i.cancel(), i.response;
	}
	sendBatch(e) {
		if (this.abortController.signal.aborted) return Mu(this.closedReason());
		if (!this.allowBatches) return Mu(/* @__PURE__ */ TypeError("JSON-RPC batches are not supported on this connection"));
		if (e.length === 0) return Mu(/* @__PURE__ */ TypeError("JSON-RPC batch must contain at least one entry"));
		let t = [], n = [], r = [];
		for (let i of e) {
			if (i.kind === "notification") {
				t.push({
					jsonrpc: "2.0",
					method: i.method,
					params: i.params
				}), r.push(Promise.resolve(void 0));
				continue;
			}
			let e = this.prepareRequest(i.method, i.params, i.mapResponse, i.options);
			t.push(e.message), r.push(e.response), n.push({
				signal: i.options?.cancellationSignal,
				cancel: e.cancel
			});
		}
		let i = t, a = this.sendWireMessage(i);
		for (let e of n) e.signal?.aborted && e.cancel();
		let o = Promise.all([a, ...r]).then(([, ...e]) => e);
		return o.catch(() => {}), o;
	}
	sendCancelRequest(e) {
		return this.sendNotification(xu, { requestId: e });
	}
	sendNotification(e, t) {
		return this.abortController.signal.aborted ? Mu(this.closedReason()) : this.sendWireMessage({
			jsonrpc: "2.0",
			method: e,
			params: t
		});
	}
	prepareRequest(e, t, n, r = {}) {
		let i = this.nextRequestId++, a = () => {}, o = new Promise((e, t) => {
			let o = {
				resolve: (r) => {
					try {
						e(n ? n(r) : r);
					} catch (e) {
						t(e);
					}
				},
				reject: t
			};
			a = () => {
				o.cancellationSent || (o.cancellationSent = !0, o.cleanup?.(), this.sendCancelRequest(i).catch(() => {}));
			}, r.cancellationSignal?.addEventListener("abort", a, { once: !0 }), o.cleanup = () => {
				r.cancellationSignal?.removeEventListener("abort", a);
			}, this.pendingResponses.set(i, o);
		});
		return o.catch(() => {}), {
			message: {
				jsonrpc: "2.0",
				id: i,
				method: e,
				params: t
			},
			response: o,
			cancel: () => a()
		};
	}
	close(e) {
		if (this.abortController.signal.aborted) return;
		let t = e ?? /* @__PURE__ */ Error("ACP connection closed");
		this.abortController.abort(t);
		for (let e of this.pendingResponses.values()) e.cleanup?.(), e.reject(t);
		this.pendingResponses.clear();
		for (let e of this.incomingRequests.values()) e.abort(t);
		this.incomingRequests.clear(), this.receiveReader?.cancel(t).catch(() => {});
	}
	initialize(e, t, n) {
		this.stream = e, this.staticHandlers = t, this.allowBatches = n?.allowBatches ?? !0, this.closedPromise = new Promise((e) => {
			this.abortController.signal.addEventListener("abort", () => e());
		}), this.receive();
	}
	legacyHandler(e, t) {
		return { handleMessage: async (n, r) => {
			if (n.kind === "request") {
				let t = await e(n.method, n.params, r);
				await n.responder.respond(t);
			} else await t(n.method, n.params, r);
			return G.yes();
		} };
	}
	async receive() {
		let e;
		try {
			let e = this.stream.readable.getReader();
			this.receiveReader = e;
			try {
				for (; !this.abortController.signal.aborted;) {
					let { value: t, done: n } = await e.read();
					if (this.abortController.signal.aborted || n) break;
					this.receiveWireMessage(t);
				}
			} finally {
				this.receiveReader === e && (this.receiveReader = void 0), e.releaseLock();
			}
		} catch (t) {
			e = t;
		} finally {
			this.close(e);
		}
	}
	receiveWireMessage(e) {
		if (Array.isArray(e)) {
			if (!this.allowBatches) {
				this.close(/* @__PURE__ */ TypeError("JSON-RPC batches are not supported on this connection"));
				return;
			}
			this.receiveBatch(e);
			return;
		}
		if (!Su(e) && !wu(e) && !Ou(e)) {
			this.sendWireMessage(Ku(K.invalidRequest(e))).catch(() => {});
			return;
		}
		this.receiveMessage(e);
	}
	receiveBatch(e) {
		if (e.length === 0) {
			this.sendWireMessage(Ku(K.invalidRequest(e))).catch(() => {});
			return;
		}
		let t = ku(e), n = t ? 0 : e.reduce((e, t) => e + +!wu(t), 0), r = e.reduce((e, t) => e + +!!wu(t), 0), i = !1, a = [], o = async () => {
			i || n !== 0 || r !== 0 || a.length === 0 || (i = !0, await this.sendWireMessage(a));
		}, s = async (e) => {
			a.push(e), --n, await o();
		};
		for (let n of e) {
			if (t) {
				Ou(n) && this.receiveMessage(n);
				continue;
			}
			if (!Su(n) && !wu(n)) {
				s(Ku(K.invalidRequest(n))).catch(() => {});
				continue;
			}
			let i = this.receiveMessage(n, Su(n) ? s : void 0, e.length);
			wu(n) && i.finally(() => {
				--r, o().catch((e) => this.close(e));
			});
		}
	}
	receiveMessage(e, t, n) {
		return this.abortController.signal.aborted ? Promise.resolve() : Tu(e) ? "method" in e ? ("id" in e || this.handleProtocolNotification(e), this.processIncomingMessage(this.toIncomingMessage(e, t, n)).catch((e) => this.close(e))) : ("id" in e ? this.handleResponse(e) : console.error("Invalid message", { message: e }), Promise.resolve()) : (console.error("Invalid message", { message: e }), Promise.resolve());
	}
	async processIncomingMessage(e) {
		if (this.abortController.signal.aborted) return;
		let t = e, n = !1;
		try {
			for (let e of [...this.staticHandlers, ...this.dynamicHandlers.values()]) {
				if (this.abortController.signal.aborted) return;
				let r = await e.handleMessage(t, this.context) ?? { handled: !0 };
				if (r.handled) return;
				t = r.message ?? t, n ||= !!r.retry;
			}
			n ? this.retryQueue.push(t) : t.kind === "request" && await t.responder.respondWithError(K.methodNotFound(t.method));
		} catch (n) {
			if (this.abortController.signal.aborted) return;
			if (t.kind === "request" && !t.responder.responded) await t.responder.respondWithResult(Lu(n, t.responder.signal));
			else {
				let t = Fu(n);
				"error" in t && console.error("Error handling notification", e.raw, t.error);
			}
		}
	}
	toIncomingMessage(e, t, n) {
		if ("id" in e) {
			let r = new AbortController();
			this.incomingRequests.set(e.id, r);
			let i = new Bu(e.id, (n) => {
				let r = {
					jsonrpc: "2.0",
					id: e.id,
					...n
				};
				return t ? t(r) : this.sendWireMessage(r);
			}, r.signal, () => {
				this.incomingRequests.get(e.id) === r && this.incomingRequests.delete(e.id);
			});
			return n !== void 0 && Vu.set(i, n), {
				kind: "request",
				method: e.method,
				params: e.params,
				raw: e,
				signal: r.signal,
				responder: i
			};
		}
		return {
			kind: "notification",
			method: e.method,
			params: e.params,
			raw: e
		};
	}
	handleResponse(e) {
		let t = this.pendingResponses.get(e.id);
		if (t) {
			if (this.pendingResponses.delete(e.id), t.cleanup?.(), !Cu(e)) t.reject(K.invalidRequest(e));
			else if ("result" in e) t.resolve(e.result);
			else {
				let { code: n, message: r, data: i } = e.error;
				t.reject(new K(n, r, i));
			}
		} else console.error("Got response to unknown request", e.id);
	}
	handleProtocolNotification(e) {
		if (e.method !== xu) return;
		let t = Au(e.params);
		if (t === void 0) return;
		let n = this.incomingRequests.get(t);
		!n || n.signal.aborted || n.abort(K.requestCancelled({ requestId: t }));
	}
	closedReason() {
		return this.abortController.signal.reason ?? /* @__PURE__ */ Error("ACP connection closed");
	}
	async sendWireMessage(e) {
		return this.abortController.signal.aborted ? Mu(this.closedReason()) : (this.writeQueue = this.writeQueue.then(async () => {
			if (this.abortController.signal.aborted) throw this.closedReason();
			let t = this.stream.writable.getWriter();
			try {
				await t.write(e);
			} finally {
				t.releaseLock();
			}
		}).catch((e) => {
			throw this.close(e), e;
		}), this.writeQueue);
	}
}, Gu = class {
	handlers = [];
	connectionName;
	name(e) {
		return this.connectionName = e, this;
	}
	withHandler(e) {
		return this.handlers.push(e), this;
	}
	onReceiveMessage(e) {
		return this.withHandler({
			handleMessage: async (t, n) => await e(t, n) ?? G.no(t),
			describe: () => this.connectionName ?? "onReceiveMessage"
		});
	}
	onReceiveRequest(e, t, n) {
		return this.withHandler({
			handleMessage: async (r, i) => r.kind !== "request" || r.method !== e ? G.no(r) : await n(t(r.params), r.responder, i) ?? G.yes(),
			describe: () => `${this.connectionName ?? "request"}:${e}`
		});
	}
	onReceiveNotification(e, t, n) {
		return this.withHandler({
			handleMessage: async (r, i) => r.kind !== "notification" || r.method !== e ? G.no(r) : await n(t(r.params), i) ?? G.yes(),
			describe: () => `${this.connectionName ?? "notification"}:${e}`
		});
	}
	connect(e, t) {
		return new Wu(e, this.handlers, t);
	}
	connectWith(e, t, n) {
		return this.connect(e, n).runUntil(t);
	}
}, K = class e extends Error {
	code;
	data;
	constructor(e, t, n) {
		super(t), this.code = e, this.name = "RequestError", this.data = n;
	}
	static parseError(t, n) {
		return new e(-32700, `Parse error${n ? `: ${n}` : ""}`, t);
	}
	static invalidRequest(t, n) {
		return new e(-32600, `Invalid request${n ? `: ${n}` : ""}`, t);
	}
	static methodNotFound(t) {
		return new e(-32601, `"Method not found": ${t}`, { method: t });
	}
	static invalidParams(t, n) {
		return new e(-32602, `Invalid params${n ? `: ${n}` : ""}`, t);
	}
	static internalError(t, n) {
		return new e(-32603, `Internal error${n ? `: ${n}` : ""}`, t);
	}
	static requestCancelled(t, n) {
		return new e(-32800, `Request cancelled${n ? `: ${n}` : ""}`, t);
	}
	static authRequired(t, n) {
		return new e(-32e3, `Authentication required${n ? `: ${n}` : ""}`, t);
	}
	static resourceNotFound(t) {
		return new e(-32002, `Resource not found${t ? `: ${t}` : ""}`, t && { uri: t });
	}
	toResult() {
		return { error: {
			code: this.code,
			message: this.message,
			data: this.data
		} };
	}
	toErrorResponse() {
		return {
			code: this.code,
			message: this.message,
			data: this.data
		};
	}
};
function Ku(e) {
	return {
		jsonrpc: "2.0",
		id: null,
		error: e.toErrorResponse()
	};
}
ts.and(P({ mode: R("form") })).and(P({ message: D() })), rs.and(P({ mode: R("url") })).and(P({ message: D() })), F([Bo, Vo]).and(P({ message: D() })), Go.and(P({ type: R("string") })), Ko.and(P({ type: R("number") })), qo.and(P({ type: R("integer") })), Jo.and(P({ type: R("boolean") })), Qo.and(P({ type: R("array") })), Yo.and(P({ type: R("string") })), du.and(P({ action: R("accept") })), P({ action: R("decline") }), P({ action: R("cancel") });
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/acp.js
function q(e) {
	return e ?? {};
}
function qu(e) {
	return typeof e == "object" && !!e && "readable" in e && "writable" in e;
}
function Ju() {
	let e = new TransformStream(), t = new TransformStream();
	return [{
		readable: t.readable,
		writable: e.writable
	}, {
		readable: e.readable,
		writable: t.writable
	}];
}
var Yu = {
	agent: {
		initialize: n.initialize,
		authenticate: n.authenticate,
		logout: n.logout,
		providers: {
			list: n.providers_list,
			set: n.providers_set,
			disable: n.providers_disable
		},
		session: {
			new: n.session_new,
			load: n.session_load,
			list: n.session_list,
			delete: n.session_delete,
			fork: n.session_fork,
			resume: n.session_resume,
			close: n.session_close,
			setMode: n.session_set_mode,
			setConfigOption: n.session_set_config_option,
			prompt: n.session_prompt,
			cancel: n.session_cancel
		},
		nes: {
			start: n.nes_start,
			suggest: n.nes_suggest,
			accept: n.nes_accept,
			reject: n.nes_reject,
			close: n.nes_close
		},
		document: {
			didOpen: n.document_did_open,
			didChange: n.document_did_change,
			didClose: n.document_did_close,
			didSave: n.document_did_save,
			didFocus: n.document_did_focus
		}
	},
	client: {
		session: {
			requestPermission: r.session_request_permission,
			update: r.session_update
		},
		fs: {
			writeTextFile: r.fs_write_text_file,
			readTextFile: r.fs_read_text_file
		},
		terminal: {
			create: r.terminal_create,
			output: r.terminal_output,
			release: r.terminal_release,
			waitForExit: r.terminal_wait_for_exit,
			kill: r.terminal_kill
		},
		elicitation: {
			create: r.elicitation_create,
			complete: r.elicitation_complete
		}
	},
	protocol: { cancelRequest: i.cancel_request }
}, Xu = Symbol("startActiveSession"), Zu = class {
	cx;
	currentRequestId;
	constructor(e, t) {
		this.cx = e, this.currentRequestId = t;
	}
	get requestId() {
		return this.currentRequestId;
	}
	get connectionContext() {
		return this.cx;
	}
	sendRequest(e, t, n, r) {
		return this.cx.sendRequest(e, t, n, r);
	}
	sendNotification(e, t) {
		return this.cx.sendNotification(e, t);
	}
	addDynamicHandler(e) {
		return this.cx.addDynamicHandler(e);
	}
}, Qu = class e extends Zu {
	constructor(e, t) {
		super(e, t);
	}
	static create(t, n) {
		return new e(t, n);
	}
	request(e, t, n) {
		let r = vd[e];
		return this.sendRequest(e, t, r?.mapResponse, n);
	}
	notify(e, t) {
		return this.sendNotification(e, t);
	}
}, $u = class e extends Zu {
	constructor(e, t) {
		super(e, t);
	}
	static create(t, n) {
		return new e(t, n);
	}
	[Xu](e, t) {
		return this.sendRequest(n.session_new, e, (e) => this.attachSession(e), t);
	}
	buildSession(e) {
		return typeof e == "string" ? sd.create(this, {
			cwd: e,
			mcpServers: []
		}) : sd.create(this, e);
	}
	attachSession(e) {
		let t = new ad(), n = this.connectionContext.signal, r = () => {
			t.fail(n.reason ?? /* @__PURE__ */ Error("ACP connection closed"));
		};
		n.aborted ? r() : n.addEventListener("abort", r);
		let i = wd(this.connectionContext).attach(e, t), a = new Hu(() => {
			n.removeEventListener("abort", r);
		});
		return cd.create(this, e, t, [i, a]);
	}
	request(e, t, n) {
		let r = _d[e];
		return this.sendRequest(e, t, r?.mapResponse, n);
	}
	notify(e, t) {
		return this.sendNotification(e, t);
	}
}, ed = class {
	connection;
	constructor(e) {
		this.connection = e;
	}
	get signal() {
		return this.connection.signal;
	}
	get closed() {
		return this.connection.closed;
	}
	close(e) {
		this.connection.close(e);
	}
}, td = class extends ed {
	connectHandlers;
	client;
	didStartConnectHandlers = !1;
	constructor(e, t = []) {
		super(e), this.connectHandlers = t, this.client = Qu.create(e.getContext());
	}
	startConnectHandlers() {
		this.didStartConnectHandlers || (this.didStartConnectHandlers = !0, Td(this, this.connectHandlers));
	}
}, nd = class extends ed {
	connectHandlers;
	agent;
	didStartConnectHandlers = !1;
	constructor(e, t = []) {
		super(e), this.connectHandlers = t, this.agent = $u.create(e.getContext());
	}
	startConnectHandlers() {
		this.didStartConnectHandlers || (this.didStartConnectHandlers = !0, Td(this, this.connectHandlers));
	}
};
function rd(e, t = []) {
	return new td(e, t);
}
function id(e, t = []) {
	return new nd(e, t);
}
var ad = class {
	values = [];
	waiters = [];
	failed = !1;
	failure;
	enqueue(e) {
		if (this.failed) return;
		let t = this.waiters.shift();
		t ? t.resolve(e) : this.values.push({
			kind: "value",
			value: e
		});
	}
	reject(e) {
		if (!this.failed) {
			if (this.waiters.length > 0) {
				for (let t of this.waiters.splice(0)) t.reject(e);
				return;
			}
			this.values.push({
				kind: "error",
				error: e
			});
		}
	}
	clearErrors() {
		this.values = this.values.filter((e) => e.kind === "value");
	}
	fail(e) {
		if (!this.failed) {
			this.failed = !0, this.failure = e;
			for (let t of this.waiters.splice(0)) t.reject(e);
		}
	}
	next() {
		if (this.values.length > 0) {
			let e = this.values.shift();
			return e.kind === "error" ? Promise.reject(e.error) : Promise.resolve(e.value);
		}
		return this.failed ? Promise.reject(this.failure) : new Promise((e, t) => {
			this.waiters.push({
				resolve: e,
				reject: t
			});
		});
	}
};
function od(e) {
	return {
		...e,
		additionalDirectories: e.additionalDirectories ? [...e.additionalDirectories] : void 0,
		mcpServers: [...e.mcpServers]
	};
}
var sd = class e {
	cx;
	request;
	constructor(e, t) {
		this.cx = e, this.request = od(t);
	}
	static create(t, n) {
		return new e(t, n);
	}
	toRequest() {
		return od(this.request);
	}
	withAdditionalDirectories(e) {
		return this.request = {
			...this.request,
			additionalDirectories: [...e]
		}, this;
	}
	withMcpServer(e) {
		return this.request = {
			...this.request,
			mcpServers: [...this.request.mcpServers, e]
		}, this;
	}
	async start(e) {
		return this.cx[Xu](this.toRequest(), e);
	}
	async withSession(e) {
		let t = await this.start();
		try {
			return await e(t);
		} finally {
			t.dispose();
		}
	}
}, cd = class e {
	cx;
	sessionResponse;
	updates;
	registrations;
	constructor(e, t, n, r) {
		this.cx = e, this.sessionResponse = t, this.updates = n, this.registrations = r;
	}
	static create(t, n, r, i) {
		return new e(t, n, r, i);
	}
	get sessionId() {
		return this.sessionResponse.sessionId;
	}
	get modes() {
		return this.sessionResponse.modes;
	}
	get meta() {
		return this.sessionResponse._meta;
	}
	get newSessionResponse() {
		return this.sessionResponse;
	}
	prompt(e, t) {
		this.updates.clearErrors();
		let r = this.cx.request(n.session_prompt, {
			sessionId: this.sessionId,
			prompt: this.promptBlocks(e)
		}, t);
		return r.then((e) => {
			this.updates.enqueue({
				kind: "stop",
				response: e,
				stopReason: e.stopReason
			});
		}, (e) => {
			this.updates.reject(e);
		}), r;
	}
	nextUpdate() {
		return this.updates.next();
	}
	async readText() {
		let e = "";
		for (;;) {
			let t = await this.nextUpdate();
			if (t.kind === "stop") return e;
			let { update: n } = t;
			n.sessionUpdate === "agent_message_chunk" && n.content.type === "text" && (e += n.content.text);
		}
	}
	dispose() {
		for (let e of this.registrations.splice(0)) e.dispose();
		this.updates.fail(/* @__PURE__ */ Error("Active session disposed"));
	}
	[Symbol.dispose]() {
		this.dispose();
	}
	promptBlocks(e) {
		return typeof e == "string" ? [{
			type: "text",
			text: e
		}] : Array.isArray(e) ? e : [e];
	}
};
function ld(e, t) {
	return e ? typeof e == "function" ? e(t) : e.parse(t) : t;
}
function J(e, t, n) {
	return {
		method: e,
		params: t,
		mapResponse: n
	};
}
function Y(e, t) {
	return {
		method: e,
		params: t
	};
}
function ud(e, t, n, r) {
	e.onReceiveRequest(t.method, (e) => ld(t.params, e), async (e, i, a) => {
		let o = await r(n(e, a, i.signal, i.id));
		await i.respond(t.mapResponse ? t.mapResponse(o) : o);
	});
}
function dd(e, t, n, r) {
	e.onReceiveNotification(t.method, (e) => ld(t.params, e), (e, t) => r(n(e, t, t.signal)));
}
function fd(e) {
	let t = {};
	for (let n of Object.values(e)) t[n.method] = n;
	return t;
}
var pd = {
	initialize: J(n.initialize, _l),
	newSession: J(n.session_new, kl),
	loadSession: J(n.session_load, Al, q),
	unstable_forkSession: J(n.session_fork, Nl),
	listSessions: J(n.session_list, jl),
	deleteSession: J(n.session_delete, Ml, q),
	resumeSession: J(n.session_resume, Pl),
	closeSession: J(n.session_close, Fl, q),
	setSessionMode: J(n.session_set_mode, Il, q),
	setSessionConfigOption: J(n.session_set_config_option, Ll),
	authenticate: J(n.authenticate, vl, q),
	unstable_listProviders: J(n.providers_list, yl),
	unstable_setProvider: J(n.providers_set, bl, q),
	unstable_disableProvider: J(n.providers_disable, xl, q),
	logout: J(n.logout, Sl, q),
	prompt: J(n.session_prompt, Rl),
	unstable_startNes: J(n.nes_start, Vl),
	unstable_suggestNes: J(n.nes_suggest, Ql),
	unstable_closeNes: J(n.nes_close, $l, q)
}, md = {
	cancel: Y(n.session_cancel, fu),
	unstable_didOpenDocument: Y(n.document_did_open, pu),
	unstable_didChangeDocument: Y(n.document_did_change, hu),
	unstable_didCloseDocument: Y(n.document_did_close, gu),
	unstable_didSaveDocument: Y(n.document_did_save, _u),
	unstable_didFocusDocument: Y(n.document_did_focus, vu),
	unstable_acceptNes: Y(n.nes_accept, yu),
	unstable_rejectNes: Y(n.nes_reject, bu)
}, hd = {
	requestPermission: J(r.session_request_permission, No),
	writeTextFile: J(r.fs_write_text_file, uo, q),
	readTextFile: J(r.fs_read_text_file, fo),
	createTerminal: J(r.terminal_create, Fo),
	terminalOutput: J(r.terminal_output, Io),
	releaseTerminal: J(r.terminal_release, Lo, q),
	waitForTerminalExit: J(r.terminal_wait_for_exit, Ro),
	killTerminal: J(r.terminal_kill, zo, q),
	createElicitation: J(r.elicitation_create, is)
}, gd = {
	sessionUpdate: Y(r.session_update, el),
	completeElicitation: Y(r.elicitation_complete, tl)
}, _d = fd(pd);
fd(md);
var vd = fd(hd), yd = fd(gd);
function bd(e, t, n, r) {
	return {
		params: e,
		requestId: r,
		signal: n,
		agent: t
	};
}
function xd(e, t, n) {
	return {
		params: e,
		signal: n,
		agent: t
	};
}
var Sd = class {
	activeSessions = /* @__PURE__ */ new Map();
	handleMessage(e) {
		if (e.kind !== "notification" || e.method !== r.session_update) return G.no(e);
		let t = el.parse(e.params), n = {
			kind: "session_update",
			notification: t,
			update: t.update
		}, i = this.activeSessions.get(t.sessionId);
		if (i && i.size > 0) for (let e of i) e.enqueue(n);
		return G.no(e);
	}
	attach(e, t) {
		let n = this.activeSessions.get(e.sessionId) ?? /* @__PURE__ */ new Set();
		return n.add(t), this.activeSessions.set(e.sessionId, n), new Hu(() => {
			n.delete(t), n.size === 0 && this.activeSessions.delete(e.sessionId);
		});
	}
}, Cd = /* @__PURE__ */ new WeakMap();
function wd(e) {
	let t = Cd.get(e);
	return t || (t = new Sd(), Cd.set(e, t)), t;
}
function Td(e, t) {
	for (let n of t) {
		let t;
		try {
			t = n(e);
		} catch (t) {
			throw e.close(t), t;
		}
		Promise.resolve(t).catch((t) => {
			e.close(t);
		});
	}
}
var Ed = Symbol("appBuilder"), Dd = Symbol("runAgentConnectHandlers"), Od = Symbol("runClientConnectHandlers"), kd = { allowBatches: !1 };
function Ad(e) {
	return new jd(e);
}
var jd = class {
	builder = Wu.builder();
	connectHandlers = [];
	constructor(e = {}) {
		e.name && this.builder.name(e.name), this.builder.withHandler({
			handleMessage: (e, t) => wd(t).handleMessage(e),
			describe: () => "client-session-update-router"
		});
	}
	[Ed]() {
		return this.builder;
	}
	[Od](e) {
		Td(e, this.connectHandlers);
	}
	connect(e) {
		return this.connectConnection(e).connection;
	}
	connectWith(e, t) {
		let { rawConnection: n, connection: r } = this.connectConnection(e);
		return n.runUntil(() => t(r.agent));
	}
	onConnect(e) {
		return this.connectHandlers.push(e), this;
	}
	onRequest(e, t, n) {
		if (n) return this.request({
			method: e,
			params: t
		}, n);
		let r = vd[e];
		if (!r) throw Error(`Unknown ACP request method '${e}'. Pass a params parser for custom methods.`);
		return this.request(r, t);
	}
	onNotification(e, t, n) {
		if (n) return this.notification({
			method: e,
			params: t
		}, n);
		let r = yd[e];
		if (!r) throw Error(`Unknown ACP notification method '${e}'. Pass a params parser for custom methods.`);
		return this.notification(r, t);
	}
	request(e, t) {
		return ud(this.builder, e, (e, t, n, r) => bd(e, $u.create(t, r), n, r), t), this;
	}
	notification(e, t) {
		return dd(this.builder, e, (e, t, n) => xd(e, $u.create(t), n), t), this;
	}
	connectConnection(e) {
		if (qu(e)) {
			let t = this.openStreamConnection(e);
			return this[Od](t.connection), t;
		}
		let [t, n] = Ju(), r = e[Ed]().connect(n, kd), i = rd(r), a = this.openStreamConnection(t);
		a.rawConnection.closed.then(() => i.close()), r.closed.then(() => a.connection.close());
		try {
			e[Dd](i), this[Od](a.connection);
		} catch (e) {
			throw i.close(e), a.connection.close(e), e;
		}
		return a;
	}
	openStreamConnection(e) {
		let t = this.builder.connect(e, kd);
		return {
			rawConnection: t,
			connection: id(t, this.connectHandlers)
		};
	}
};
n.initialize, n.authenticate, n.providers_list, n.providers_set, n.providers_disable, n.session_new, n.session_load, n.session_set_mode, n.session_set_config_option, n.session_prompt, n.session_list, n.session_delete, n.session_fork, n.session_resume, n.session_close, n.logout, n.nes_start, n.nes_suggest, n.nes_close, n.session_cancel, n.nes_accept, n.nes_reject, n.document_did_open, n.document_did_change, n.document_did_close, n.document_did_save, n.document_did_focus, r.session_request_permission, r.fs_write_text_file, r.fs_read_text_file, r.terminal_create, r.terminal_output, r.terminal_release, r.terminal_wait_for_exit, r.terminal_kill, r.elicitation_create, r.session_update, r.elicitation_complete;
//#endregion
//#region src/core/protocol/normalize.ts
var Md = 1e3, Nd = 256, Pd = 16384, Fd = 256, Id = 1048576, Ld = 8388608, Rd = 1048576, zd = 4096, Bd = 4194304, Vd = 4096, Hd = 16;
function X(e) {
	return typeof e == "object" && !!e && !Array.isArray(e);
}
function Z(e, t = Pd) {
	return typeof e == "string" ? pf(e, t) : void 0;
}
function Ud(e) {
	let t = Z(e, Pd);
	if (t) try {
		let e = new URL(t).protocol;
		return e === "http:" || e === "https:" ? t : void 0;
	} catch {
		return;
	}
}
function Q(e, t = Nd) {
	return Array.isArray(e) ? e.slice(0, t).filter(X) : [];
}
function Wd(e) {
	return Array.isArray(e) ? e.slice(0, Fd).flatMap((e) => {
		let t = sf(e);
		return t ? [t] : [];
	}) : [];
}
function Gd(e) {
	let t = df(e, { nodes: Vd }, 0);
	return X(t) ? t : void 0;
}
function Kd(e) {
	return Q(e).map((e, t) => ({
		id: Z(e.methodId) ?? Z(e.id) ?? `auth-${t}`,
		name: Z(e.name) ?? Z(e.title) ?? `Authentication ${t + 1}`,
		...Z(e.description) ? { description: Z(e.description) } : {},
		type: Z(e.type) ?? "agent",
		raw: Gd(e) ?? {}
	}));
}
function qd(e) {
	return Q(e).flatMap((e) => {
		let t = Z(e.name);
		if (!t) return [];
		let n = X(e.input) ? e.input : void 0;
		return [{
			name: t,
			description: Z(e.description) ?? "",
			...n && Z(n.hint) ? { inputHint: Z(n.hint) } : {}
		}];
	});
}
function Jd(e) {
	return Q(e).flatMap((e) => {
		let t = Z(e.configId) ?? Z(e.id);
		if (!t) return [];
		let n = Z(e.type), r = e.currentValue, i = n === "boolean" || typeof r == "boolean" ? "boolean" : n === "select" || Array.isArray(e.options) ? "select" : "unknown", a = typeof r == "boolean" ? r : Z(r) ?? "", o = Q(e.options).flatMap((e) => {
			let t = Z(e.value);
			return t ? [{
				value: t,
				name: Z(e.name) ?? t,
				...Z(e.description) ? { description: Z(e.description) } : {}
			}] : [];
		});
		return [{
			id: t,
			name: Z(e.name) ?? t,
			...Z(e.description) ? { description: Z(e.description) } : {},
			...Z(e.category) ? { category: Z(e.category) } : {},
			type: i,
			currentValue: a,
			...o.length ? { options: o } : {}
		}];
	});
}
function Yd(e) {
	if (!X(e)) return [];
	let t = Q(e.availableModes), n = Z(e.currentModeId) ?? "";
	return t.length ? [{
		id: "mode",
		name: "Mode",
		category: "mode",
		type: "select",
		currentValue: n,
		options: t.flatMap((e) => {
			let t = Z(e.id);
			return t ? [{
				value: t,
				name: Z(e.name) ?? t,
				...Z(e.description) ? { description: Z(e.description) } : {}
			}] : [];
		})
	}] : [];
}
function Xd(e) {
	if (!X(e)) return { sessions: [] };
	let t = Q(e.sessions).flatMap((e) => {
		let t = Z(e.sessionId);
		return t ? [{
			sessionId: t,
			...Z(e.title) ? { title: Z(e.title) } : {},
			...Z(e.updatedAt) ? { updatedAt: Z(e.updatedAt) } : {},
			...Z(e.cwd) ? { cwd: Z(e.cwd) } : {}
		}] : [];
	}), n = Z(e.nextCursor);
	return {
		sessions: t,
		...n ? { nextCursor: n } : {}
	};
}
function Zd(e) {
	if (!X(e) || !gf(e.used) || !gf(e.size)) return;
	let t = X(e.cost) ? Z(e.cost.currency) : void 0, n = X(e.cost) && gf(e.cost.amount) && t !== void 0 ? {
		amount: e.cost.amount,
		currency: t
	} : void 0;
	return {
		used: e.used,
		size: e.size,
		...n ? { cost: n } : {}
	};
}
var Qd = class {
	#e = [];
	#t = 0;
	#n = /* @__PURE__ */ new Map();
	#r;
	#i = /* @__PURE__ */ new Set();
	#a = /* @__PURE__ */ new Map();
	get activities() {
		return this.#e;
	}
	reset() {
		this.#e = [], this.#n.clear(), this.#r = void 0, this.#i.clear(), this.#a.clear();
	}
	beginTurn() {
		this.#n.clear(), this.#i.clear();
	}
	addUserMessage(e, t) {
		let n = `local-user-${++this.#t}`;
		return this.#g({
			type: "message",
			id: n,
			role: "user",
			content: Wd(e),
			...t ? { pending: !0 } : {}
		}), t && (this.#r = n), n;
	}
	markUserAccepted(e = []) {
		if (this.#r) {
			this.#m(this.#r, (e) => e.type === "message" ? {
				...e,
				pending: !1
			} : e);
			for (let t of e) {
				let e = {
					type: "context",
					id: `local-context-${++this.#t}`,
					contextId: t.id,
					label: t.label,
					content: t.content
				};
				this.#g(e);
			}
			this.#i = new Set(e.map((e) => e.id));
		}
	}
	reduce(e, t) {
		if (!X(e) || typeof e.sessionUpdate != "string") return { unsupported: "invalid_update" };
		let n = Z(e.sessionUpdate) ?? "";
		switch (n) {
			case "user_message_chunk":
			case "agent_message_chunk":
			case "agent_thought_chunk": {
				let r = n === "user_message_chunk" ? "user" : n === "agent_message_chunk" ? "assistant" : "thought";
				return this.#o(r, Z(e.messageId), e.content, t), {};
			}
			case "user_message":
			case "agent_message":
			case "agent_thought": {
				let t = n === "user_message" ? "user" : n === "agent_message" ? "assistant" : "thought";
				return this.#s(t, Z(e.messageId), e), {};
			}
			case "tool_call":
			case "tool_call_update": return this.#c(e), {};
			case "tool_call_content_chunk": return this.#l(e), {};
			case "plan":
			case "plan_update": return this.#u(e), {};
			case "plan_removed": return this.#h(`plan:${Z(e.planId) ?? "primary"}`), {};
			case "terminal_update": return this.#d(e), {};
			case "terminal_output_chunk": return this.#f(e), {};
			case "available_commands_update": return { commands: qd(e.availableCommands) };
			case "config_option_update": return { configOptions: Jd(e.configOptions) };
			case "current_mode_update": return {};
			case "session_info_update": return { sessionTitle: Object.hasOwn(e, "title") ? Z(e.title) ?? null : void 0 };
			case "usage_update": return { usage: Zd(e) };
			case "state_update": {
				let t = Z(e.state);
				return t === "running" || t === "requires_action" || t === "idle" ? {
					state: t,
					...Z(e.stopReason) ? { stopReason: Z(e.stopReason) } : {}
				} : { unsupported: `state:${t ?? "missing"}` };
			}
			default: return { unsupported: n };
		}
	}
	#o(e, t, n, r) {
		if (e === "user" && this.#r && ef(n, this.#i)) return;
		let i = t;
		if (!i && r === 1 && (i = this.#n.get(e) ?? `v1-${e}-${++this.#t}`, this.#n.set(e, i)), !i) return;
		let a = tf(e, i);
		if (e === "user" && this.#r) {
			let e = this.#r, t = this.#e.find((t) => t.type === "message" && t.id === e);
			t?.type === "message" && (this.#m(e, () => ({
				...t,
				id: a,
				pending: !1
			})), this.#r = void 0, this.#i.clear());
		}
		let o = this.#e.find((e) => e.type === "message" && e.id === a), s = sf(n);
		s && (o?.type === "message" ? this.#m(a, () => ({
			...o,
			content: af(o.content, s)
		})) : this.#g({
			type: "message",
			id: a,
			role: e,
			content: [s]
		}));
	}
	#s(e, t, n) {
		if (!t) return;
		let r = tf(e, t);
		if (e === "user" && this.#r) {
			let e = this.#r, t = this.#e.find((t) => t.type === "message" && t.id === e);
			if (t?.type === "message") {
				let i = Object.hasOwn(n, "content") ? $d(n.content, this.#i) : t.content;
				this.#m(e, () => ({
					...t,
					id: r,
					content: i,
					pending: !1
				})), this.#r = void 0, this.#i.clear();
				return;
			}
		}
		let i = this.#e.find((e) => e.type === "message" && e.id === r), a = Object.hasOwn(n, "content") ? Wd(n.content) : i?.type === "message" ? i.content : [];
		i?.type === "message" ? this.#m(r, () => ({
			...i,
			role: e,
			content: a
		})) : this.#g({
			type: "message",
			id: r,
			role: e,
			content: a
		});
	}
	#c(e) {
		let t = Z(e.toolCallId);
		if (!t) return;
		let n = `tool:${t}`, r = this.#e.find((e) => e.type === "tool" && e.id === n), { subagent: i, ...a } = r?.type === "tool" ? r : {
			type: "tool",
			id: n,
			title: "Tool",
			status: "pending",
			content: [],
			locations: []
		}, o = {
			...a,
			...Object.hasOwn(e, "title") ? { title: Z(e.title) ?? "Tool" } : {},
			...Object.hasOwn(e, "kind") && Z(e.kind) ? { kind: Z(e.kind) } : {},
			...Object.hasOwn(e, "status") ? { status: Z(e.status) ?? "pending" } : {},
			...Object.hasOwn(e, "content") ? { content: cf(e.content) } : {},
			...Object.hasOwn(e, "locations") ? { locations: cf(e.locations).filter(X) } : {},
			...Object.hasOwn(e, "rawInput") ? { rawInput: lf(e.rawInput) } : {},
			...Object.hasOwn(e, "rawOutput") ? { rawOutput: lf(e.rawOutput) } : {}
		}, s = nf(o), c = {
			...o,
			...s ? { subagent: s } : {}
		};
		this.#p(n, c);
	}
	#l(e) {
		let t = Z(e.toolCallId);
		if (!t || !Object.hasOwn(e, "content")) return;
		let n = `tool:${t}`, r = this.#e.find((e) => e.type === "tool" && e.id === n), i = r?.type === "tool" ? r : {
			type: "tool",
			id: n,
			title: "Tool",
			status: "pending",
			content: [],
			locations: []
		};
		i.content.length >= Nd || this.#p(n, {
			...i,
			content: cf([...i.content, e.content])
		});
	}
	#u(e) {
		let t = X(e.plan) ? e.plan : e, n = `plan:${Z(t.planId) ?? "primary"}`, r = {
			type: "plan",
			id: n,
			entries: Q(t.entries).map((e) => ({
				content: Z(e.content) ?? "",
				...Z(e.priority) ? { priority: Z(e.priority) } : {},
				status: Z(e.status) ?? "pending"
			}))
		};
		this.#p(n, r);
	}
	#d(e) {
		let t = Z(e.terminalId);
		if (!t) return;
		let n = `terminal:${t}`;
		if (Object.hasOwn(e, "output") && X(e.output) && typeof e.output.data == "string") {
			let n = new TextDecoder(), r = of(e.output.data).subarray(0, Bd), i = ff(n.decode(r, { stream: !0 }), Rd);
			this.#a.set(t, {
				decoder: n,
				output: i,
				chunks: 1,
				decodedBytes: r.byteLength
			});
		}
		let r = this.#e.find((e) => e.type === "terminal" && e.id === n), i = Array.isArray(e.command) ? e.command.filter((e) => typeof e == "string").join(" ") : Z(e.command), a = this.#a.get(t)?.output ?? "", o = {
			type: "terminal",
			id: n,
			title: i ?? (r?.type === "terminal" ? r.title : "Terminal"),
			output: a,
			exited: Object.hasOwn(e, "exitStatus") ? e.exitStatus !== null : r?.type === "terminal" && r.exited
		};
		this.#p(n, o);
	}
	#f(e) {
		let t = Z(e.terminalId), n = Z(e.data);
		if (!t || !n) return;
		let r = this.#a.get(t) ?? {
			decoder: new TextDecoder(),
			output: "",
			chunks: 0,
			decodedBytes: 0
		};
		if (r.chunks >= zd || r.decodedBytes >= Bd) return;
		let i = Bd - r.decodedBytes, a = of(n).subarray(0, i);
		r.chunks += 1, r.decodedBytes += a.byteLength, r.output = ff(r.output + r.decoder.decode(a, { stream: !0 }), Rd), this.#a.set(t, r);
		let o = `terminal:${t}`, s = this.#e.find((e) => e.type === "terminal" && e.id === o), c = s?.type === "terminal" ? {
			...s,
			output: r.output
		} : {
			type: "terminal",
			id: o,
			title: "Terminal",
			output: r.output,
			exited: !1
		};
		this.#p(o, c);
	}
	#p(e, t) {
		let n = this.#e.findIndex((t) => t.id === e);
		if (n < 0) {
			this.#g(t);
			return;
		}
		this.#e = this.#e.map((e, r) => r === n ? t : e);
	}
	#m(e, t) {
		this.#e = this.#e.map((n) => n.id === e ? t(n) : n);
	}
	#h(e) {
		this.#e = this.#e.filter((t) => t.id !== e);
	}
	#g(e) {
		if (this.#e = [...this.#e, e], this.#e.length <= Md) return;
		let t = this.#e.slice(0, this.#e.length - Md);
		this.#e = this.#e.slice(-1e3);
		for (let e of t) e.id === this.#r && (this.#r = void 0), e.type === "terminal" && this.#a.delete(e.id.slice(9));
	}
};
function $d(e, t) {
	return Array.isArray(e) ? Wd(e.filter((e) => !ef(e, t))) : [];
}
function ef(e, t) {
	if (!X(e) || !X(e._meta)) return !1;
	let n = e._meta["pretty-aui/context"];
	return X(n) && n.version === 1 && typeof n.id == "string" && t.has(n.id);
}
function tf(e, t) {
	return `message:${e}:${t}`;
}
function nf(e) {
	if (e.kind !== "think" || !X(e.rawInput)) return;
	let t = Z(e.rawInput.subagent_type), n = Z(e.rawInput.description), r = Z(e.rawInput.prompt);
	if (!t || !n || !r) return;
	let i = X(e.rawOutput) && X(e.rawOutput.metadata) ? e.rawOutput.metadata : void 0, a = rf(i?.sessionId), o = rf(e.rawInput.task_id), s = a ?? o, c = e.rawInput.background === !0 || i?.background === !0;
	return {
		agent: t,
		...n ? { description: n } : {},
		...s ? { sessionId: s } : {},
		background: c
	};
}
function rf(e) {
	return typeof e == "string" && e.length > 0 && e.length <= Pd ? e : void 0;
}
function af(e, t) {
	let n = e.at(-1);
	return n?.type === "text" && typeof n.text == "string" && t.type === "text" && typeof t.text == "string" && n.annotations == null && n._meta == null && t.annotations == null && t._meta == null ? [...e.slice(0, -1), {
		type: "text",
		text: ff(n.text + t.text, Id)
	}] : e.length >= Fd ? [...e] : [...e, t];
}
function of(e) {
	try {
		if (typeof globalThis.atob == "function") {
			let t = globalThis.atob(e.slice(0, Ld));
			return Uint8Array.from(t, (e) => e.charCodeAt(0));
		}
		return new Uint8Array(Buffer.from(e.slice(0, Ld), "base64"));
	} catch {
		return /* @__PURE__ */ new Uint8Array();
	}
}
function sf(e) {
	if (!X(e)) return;
	let t = Z(e.type, 128);
	if (!t) return;
	let n = { type: t };
	if (t === "text") {
		let t = Z(e.text, Id);
		return t === void 0 ? void 0 : {
			...n,
			type: "text",
			text: t
		};
	}
	if (t === "image" || t === "audio") {
		let r = Z(e.data, Ld), i = Z(e.mimeType, 256);
		return r === void 0 || i === void 0 ? void 0 : {
			...n,
			type: t,
			data: r,
			mimeType: i
		};
	}
	if (t === "resource_link") {
		let t = _f(e.uri), r = Z(e.name, Pd);
		return !t || !r ? void 0 : {
			...n,
			type: "resource_link",
			uri: t,
			name: r,
			...Z(e.title) ? { title: Z(e.title) } : {},
			...Z(e.description) ? { description: Z(e.description) } : {},
			...Z(e.mimeType, 256) ? { mimeType: Z(e.mimeType, 256) } : {},
			...typeof e.size == "number" && Number.isFinite(e.size) ? { size: e.size } : {}
		};
	}
	if (t === "resource" && X(e.resource)) {
		let t = _f(e.resource.uri);
		return t ? {
			...n,
			type: "resource",
			resource: {
				uri: t,
				...Z(e.resource.mimeType, 256) ? { mimeType: Z(e.resource.mimeType, 256) } : {},
				...Z(e.resource.text, 1048576) === void 0 ? {} : { text: Z(e.resource.text, Id) },
				...Z(e.resource.blob, 8388608) === void 0 ? {} : { blob: Z(e.resource.blob, Ld) }
			}
		} : void 0;
	}
	return n;
}
function cf(e) {
	if (!Array.isArray(e)) return [];
	let t = df(e, { nodes: Vd }, 0);
	return Array.isArray(t) ? t : [];
}
function lf(e) {
	let t = df(e, { nodes: Vd }, 0);
	return t === uf ? null : t;
}
var uf = Symbol("omit-structured-value");
function df(e, t, n) {
	if (t.nodes <= 0 || n > Hd) return uf;
	if (--t.nodes, typeof e == "string") return pf(e, Id);
	if (e === null || typeof e == "boolean" || typeof e == "number" && Number.isFinite(e)) return e;
	if (Array.isArray(e)) {
		let r = [];
		for (let i of e.slice(0, Nd)) {
			let e = df(i, t, n + 1);
			if (e !== uf && r.push(e), t.nodes <= 0) break;
		}
		return r;
	}
	if (X(e)) {
		let r = {};
		for (let [i, a] of Object.entries(e).slice(0, Nd)) {
			let e = df(a, t, n + 1);
			if (e !== uf && (r[pf(i, Pd)] = e), t.nodes <= 0) break;
		}
		return r;
	}
	return null;
}
function ff(e, t) {
	if (e.length <= t) return e;
	let n = e.length - t;
	return hf(e.charCodeAt(n)) && (n += 1), e.slice(n);
}
function pf(e, t) {
	if (e.length <= t) return e;
	let n = t;
	return mf(e.charCodeAt(n - 1)) && --n, e.slice(0, n);
}
function mf(e) {
	return e >= 55296 && e <= 56319;
}
function hf(e) {
	return e >= 56320 && e <= 57343;
}
function gf(e) {
	return typeof e == "number" && Number.isFinite(e) && e >= 0 && !Object.is(e, -0);
}
function _f(e) {
	let t = Z(e, Pd);
	if (t) try {
		let e = new URL(t).protocol;
		return e === "http:" || e === "https:" || e === "file:" ? t : void 0;
	} catch {
		return;
	}
}
//#endregion
//#region src/core/protocol/interactions.ts
function vf(e) {
	return Q(e).map((e, t) => ({
		id: Z(e.optionId) ?? `option-${t}`,
		name: Z(e.name) ?? `Option ${t + 1}`,
		kind: Z(e.kind) ?? "unknown"
	}));
}
function yf(e) {
	let t = X(e) ? e : {}, n = t.mode === "form" || t.mode === "url" ? t.mode : "unknown", r = Z(t.elicitationId), i = Gd(t.requestedSchema), a = Ud(t.url);
	return {
		type: "elicitation",
		...r ? { elicitationId: r } : {},
		mode: n,
		message: Z(t.message) ?? "The agent needs more information.",
		...a ? { url: a } : {},
		...i ? { requestedSchema: i } : {}
	};
}
function bf(e) {
	return { outcome: e };
}
function xf(e) {
	return e.action === "accept" ? {
		action: "accept",
		...e.content ? { content: Object.fromEntries(Object.entries(e.content).map(([e, t]) => [e, Array.isArray(t) ? [...t] : t])) } : {}
	} : { action: e.action };
}
//#endregion
//#region src/core/protocol/types.ts
function Sf(e, t, n, r) {
	if (!Df(e.cwd)) throw $(`ACP cwd must be an absolute path: ${e.cwd}`, n, r);
	if (e.additionalDirectories?.some((e) => !Df(e))) throw $("ACP additionalDirectories must contain only absolute paths", n, r);
	if (e.additionalDirectories?.length && !t.additionalDirectories) throw $("The agent does not support additionalDirectories", n, r);
	if ((e.additionalDirectories?.length ?? 0) > 64) throw $("ACP additionalDirectories is limited to 64 entries", n, r);
	if ((e.mcpServers?.length ?? 0) > 32) throw $("ACP MCP configuration is limited to 32 servers", n, r);
	for (let i of e.mcpServers ?? []) Ef(i, t, n, r);
}
function Cf(e, t, n) {
	if (e.length > 256) throw $("ACP prompts are limited to 256 content blocks", n, "prompt");
	for (let r of e) if (Tf(r, n), r.type !== "text" && r.type !== "resource_link" && !(r.type === "image" && t.image) && !(r.type === "audio" && t.audio) && !(r.type === "resource" && t.embeddedContext)) throw $(`The agent does not support prompt content type '${r.type}'`, n, "prompt");
}
async function wf(t, n, r) {
	try {
		return await t();
	} catch (t) {
		throw t instanceof K ? t.code === -32e3 ? new e("AUTHENTICATION_REQUIRED", "The agent requires authentication for this session operation", {
			cause: t,
			protocol: n,
			phase: r
		}) : new e("SESSION_REJECTED", `The agent rejected ${r}`, {
			cause: t,
			protocol: n,
			phase: r,
			retryable: r === "session/open"
		}) : t;
	}
}
function Tf(e, t) {
	if (e.type === "text" && typeof e.text == "string" && e.text.length > 1048576) throw $("ACP text content is limited to 1 MiB", t, "prompt");
	if ((e.type === "image" || e.type === "audio") && typeof e.data == "string" && e.data.length > 8388608) throw $("ACP media content is limited to 8 MiB of base64 data", t, "prompt");
	if (e.type === "resource" && typeof e.resource == "object" && e.resource !== null) {
		let n = e.resource;
		if (typeof n.text == "string" && n.text.length > 1048576) throw $("ACP embedded resource text is limited to 1 MiB", t, "prompt");
		if (typeof n.blob == "string" && n.blob.length > 8388608) throw $("ACP embedded resource data is limited to 8 MiB", t, "prompt");
	}
}
function Ef(e, t, n, r) {
	if (e.type === "sse" && n !== 1) throw $("SSE MCP servers are available only with protocol: 1", n, r);
	if (!t.mcp[e.type]) throw $(`The agent does not support ${e.type} MCP servers`, n, r);
}
function $(t, n, r) {
	return new e("INVALID_CONFIGURATION", t, {
		...n === void 0 ? {} : { protocol: n },
		phase: r
	});
}
function Df(e) {
	return e.startsWith("/") || /^[A-Za-z]:[\\/]/.test(e) || e.startsWith("\\\\");
}
//#endregion
export { N as A, M as B, Cu as C, lo as D, co as E, k as F, t as G, Pi as H, P as I, L, A as M, I as N, B as O, R as P, D as R, Tu as S, z as T, n as U, sa as V, e as W, Yu as _, yf as a, Hu as b, Qd as c, X as d, Kd as f, Ad as g, Xd as h, xf as i, j, V as k, Z as l, Yd as m, Cf as n, vf as o, Jd as p, Sf as r, bf as s, wf as t, Gd as u, Wu as v, Ku as w, K as x, G as y, F as z };

//# sourceMappingURL=types.js.map