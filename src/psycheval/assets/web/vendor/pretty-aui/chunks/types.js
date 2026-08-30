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
//#region src/core/prompt-envelope.ts
var n = "pretty-aui-user-message-v1-", r = 32, i = `[a-f0-9]{${r}}`, a = 16384, o = 160, s = RegExp(`(?:[\\t ]*\\r?\\n){0,2}[\\t ]*<${n}(${i})>[\\t ]*\\r?\\n`, "g"), c = RegExp(`(?:[\\t ]*\\r?\\n)?[\\t ]*</${n}(${i})>`, "g"), l = RegExp(`${n}${i}`, "g"), u = 0;
function d() {
	let e = /* @__PURE__ */ new Uint8Array(16);
	try {
		if (typeof globalThis.crypto?.getRandomValues == "function") return globalThis.crypto.getRandomValues(e), Array.from(e, (e) => e.toString(16).padStart(2, "0")).join("");
	} catch {}
	return u += 1, `${Date.now().toString(16).padStart(12, "0").slice(-12)}${u.toString(16).padStart(8, "0").slice(-8)}${Math.floor(Math.random() * 281474976710656).toString(16).padStart(12, "0")}`;
}
function f(e, t) {
	if (!t || t.length !== r || !/^[a-f0-9]+$/.test(t)) throw Error("Prompt envelope tokens must be bounded lowercase IDs");
	let i = `${n}${t}`;
	return [
		{
			type: "text",
			text: `\n\n<${i}>\n`
		},
		...e,
		{
			type: "text",
			text: `\n</${i}>`
		}
	];
}
function p(e) {
	let t = [], n = /* @__PURE__ */ new Map(), r, i = !1, a = -1, o = 0, u = "";
	for (let d of e) {
		let e = o;
		if (d.type !== "text" || typeof d.text != "string") {
			o += 1, t.push({
				block: d,
				start: e,
				end: o
			}), u = "";
			continue;
		}
		o += d.text.length, t.push({
			block: d,
			start: e,
			end: o
		});
		let f = u + d.text, p = e - u.length;
		l.lastIndex = 0;
		for (let e = l.exec(f); e;) i = !0, a = Math.max(a, p + e.index + e[0].length), e = l.exec(f);
		let ee = [];
		for (let [t, n] of [["opening", s], ["closing", c]]) {
			n.lastIndex = 0;
			for (let r = n.exec(f); r;) {
				let i = p + r.index, a = i + r[0].length;
				a > e && ee.push({
					kind: t,
					token: r[1],
					start: i,
					end: a
				}), r = n.exec(f);
			}
		}
		ee.sort((e, t) => e.start - t.start);
		for (let e of ee) {
			if (e.kind === "opening") {
				n.set(e.token, e);
				continue;
			}
			let t = n.get(e.token);
			t && t.end <= e.start && (r = {
				opening: t,
				closing: e
			});
		}
		u = f.slice(-256);
	}
	return r ? a > r.closing.end ? {
		status: "malformed",
		content: [...e]
	} : {
		status: "restored",
		content: ee(t, r.opening.end, r.closing.start),
		context: te(ee(t, 0, r.opening.start), r.opening.token)
	} : {
		status: i ? "malformed" : "none",
		content: [...e]
	};
}
function ee(e, t, n) {
	let r = [];
	for (let i of e) {
		if (i.block.type === "text" && typeof i.block.text == "string") {
			let e = Math.max(i.start, t), a = Math.min(i.end, n);
			if (e < a) {
				let t = i.block.text.slice(e - i.start, a - i.start);
				r.push({
					...i.block,
					type: "text",
					text: t
				});
			}
			continue;
		}
		i.start >= t && i.end <= n && r.push(i.block);
	}
	return r;
}
function te(e, t) {
	let n = [];
	for (let r of e) {
		let e = ne(r), i = n.at(-1);
		if (e && i?.metadata && i.id === e.id && i.label === e.label) {
			i.content.push(r);
			continue;
		}
		if (!e && i && !i.metadata) {
			i.content.push(r);
			continue;
		}
		let a = n.length;
		n.push(e ? {
			...e,
			content: [r],
			metadata: !0
		} : {
			id: `restored:${t}:${a}`,
			label: re([r]),
			content: [r],
			metadata: !1
		});
	}
	return n.map((e) => ({
		id: e.id,
		label: e.metadata ? e.label : re(e.content),
		content: e.content
	}));
}
function ne(e) {
	if (!ie(e._meta)) return;
	let t = e._meta["pretty-aui/context"];
	if (!(!ie(t) || t.version !== 1 || typeof t.id != "string" || !t.id.trim() || t.id.length > a || typeof t.label != "string" || !t.label.trim() || t.label.length > a)) return {
		id: t.id,
		label: t.label
	};
}
function re(e) {
	for (let t of e) {
		if (t.type === "text" && typeof t.text == "string") {
			let e = t.text.split(/\r?\n/u).map((e) => e.trim()).find(Boolean);
			if (e) return e.slice(0, o);
		}
		if (t.type === "resource" && ie(t.resource)) {
			let e = t.resource.uri;
			if (typeof e == "string" && e) return e.slice(0, o);
		}
		if (t.type === "resource_link") {
			for (let e of [
				t.title,
				t.name,
				t.uri
			]) if (typeof e == "string" && e) return e.slice(0, o);
		}
		if ((t.type === "image" || t.type === "audio") && typeof t.mimeType == "string" && t.mimeType) return t.mimeType.slice(0, o);
		if (typeof t.type == "string" && t.type) return t.type.slice(0, o);
	}
	return "restored context";
}
function ie(e) {
	return typeof e == "object" && !!e && !Array.isArray(e);
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/schema/index.js
var m = {
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
}, h = {
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
}, ae = { cancel_request: "$/cancel_request" }, oe, se = /*@__PURE__*/ Object.freeze({ status: "aborted" });
function g(e, t, n) {
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
var ce = class extends Error {
	constructor() {
		super("Encountered Promise during synchronous parse. Use .parseAsync() instead.");
	}
}, le = class extends Error {
	constructor(e) {
		super(`Encountered unidirectional transform during encode: ${e}`), this.name = "ZodEncodeError";
	}
};
(oe = globalThis).__zod_globalConfig ?? (oe.__zod_globalConfig = {});
var ue = globalThis.__zod_globalConfig;
function _(e) {
	return e && Object.assign(ue, e), ue;
}
//#endregion
//#region node_modules/.pnpm/zod@4.4.3/node_modules/zod/v4/core/util.js
function de(e) {
	let t = Object.values(e).filter((e) => typeof e == "number");
	return Object.entries(e).filter(([e, n]) => t.indexOf(+e) === -1).map(([e, t]) => t);
}
function fe(e, t) {
	return typeof t == "bigint" ? t.toString() : t;
}
function pe(e) {
	return { get value() {
		{
			let t = e();
			return Object.defineProperty(this, "value", { value: t }), t;
		}
	} };
}
function me(e) {
	return e == null;
}
function he(e) {
	let t = +!!e.startsWith("^"), n = e.endsWith("$") ? e.length - 1 : e.length;
	return e.slice(t, n);
}
function ge(e, t) {
	let n = e / t, r = Math.round(n), i = 2 ** -52 * Math.max(Math.abs(n), 1);
	return Math.abs(n - r) < i ? 0 : n - r;
}
var _e = /* @__PURE__*/ Symbol("evaluating");
function v(e, t, n) {
	let r;
	Object.defineProperty(e, t, {
		get() {
			if (r !== _e) return r === void 0 && (r = _e, r = n()), r;
		},
		set(n) {
			Object.defineProperty(e, t, { value: n });
		},
		configurable: !0
	});
}
function ve(e, t, n) {
	Object.defineProperty(e, t, {
		value: n,
		writable: !0,
		enumerable: !0,
		configurable: !0
	});
}
function ye(...e) {
	let t = {};
	for (let n of e) {
		let e = Object.getOwnPropertyDescriptors(n);
		Object.assign(t, e);
	}
	return Object.defineProperties({}, t);
}
function be(e) {
	return JSON.stringify(e);
}
function xe(e) {
	return e.toLowerCase().trim().replace(/[^\w\s-]/g, "").replace(/[\s_-]+/g, "-").replace(/^-+|-+$/g, "");
}
var Se = "captureStackTrace" in Error ? Error.captureStackTrace : (...e) => {};
function Ce(e) {
	return typeof e == "object" && !!e && !Array.isArray(e);
}
var we = /* @__PURE__*/ pe(() => {
	if (ue.jitless || typeof navigator < "u" && navigator?.userAgent?.includes("Cloudflare")) return !1;
	try {
		return Function(""), !0;
	} catch {
		return !1;
	}
});
function Te(e) {
	if (Ce(e) === !1) return !1;
	let t = e.constructor;
	if (t === void 0 || typeof t != "function") return !0;
	let n = t.prototype;
	return Ce(n) !== !1 && Object.prototype.hasOwnProperty.call(n, "isPrototypeOf") !== !1;
}
function Ee(e) {
	return Te(e) ? { ...e } : Array.isArray(e) ? [...e] : e instanceof Map ? new Map(e) : e instanceof Set ? new Set(e) : e;
}
var De = /* @__PURE__*/ new Set([
	"string",
	"number",
	"symbol"
]);
function Oe(e) {
	return e.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
function y(e, t, n) {
	let r = new e._zod.constr(t ?? e._zod.def);
	return (!t || n?.parent) && (r._zod.parent = e), r;
}
function b(e) {
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
function ke(e) {
	return Object.keys(e).filter((t) => e[t]._zod.optin === "optional" && e[t]._zod.optout === "optional");
}
var Ae = {
	safeint: [-(2 ** 53 - 1), 2 ** 53 - 1],
	int32: [-2147483648, 2147483647],
	uint32: [0, 4294967295],
	float32: [-34028234663852886e22, 34028234663852886e22],
	float64: [-Number.MAX_VALUE, Number.MAX_VALUE]
};
function je(e, t) {
	let n = e._zod.def, r = n.checks;
	if (r && r.length > 0) throw Error(".pick() cannot be used on object schemas containing refinements");
	return y(e, ye(e._zod.def, {
		get shape() {
			let e = {};
			for (let r in t) {
				if (!(r in n.shape)) throw Error(`Unrecognized key: "${r}"`);
				t[r] && (e[r] = n.shape[r]);
			}
			return ve(this, "shape", e), e;
		},
		checks: []
	}));
}
function Me(e, t) {
	let n = e._zod.def, r = n.checks;
	if (r && r.length > 0) throw Error(".omit() cannot be used on object schemas containing refinements");
	return y(e, ye(e._zod.def, {
		get shape() {
			let r = { ...e._zod.def.shape };
			for (let e in t) {
				if (!(e in n.shape)) throw Error(`Unrecognized key: "${e}"`);
				t[e] && delete r[e];
			}
			return ve(this, "shape", r), r;
		},
		checks: []
	}));
}
function Ne(e, t) {
	if (!Te(t)) throw Error("Invalid input to extend: expected a plain object");
	let n = e._zod.def.checks;
	if (n && n.length > 0) {
		let n = e._zod.def.shape;
		for (let e in t) if (Object.getOwnPropertyDescriptor(n, e) !== void 0) throw Error("Cannot overwrite keys on object schemas containing refinements. Use `.safeExtend()` instead.");
	}
	return y(e, ye(e._zod.def, { get shape() {
		let n = {
			...e._zod.def.shape,
			...t
		};
		return ve(this, "shape", n), n;
	} }));
}
function Pe(e, t) {
	if (!Te(t)) throw Error("Invalid input to safeExtend: expected a plain object");
	return y(e, ye(e._zod.def, { get shape() {
		let n = {
			...e._zod.def.shape,
			...t
		};
		return ve(this, "shape", n), n;
	} }));
}
function Fe(e, t) {
	if (e._zod.def.checks?.length) throw Error(".merge() cannot be used on object schemas containing refinements. Use .safeExtend() instead.");
	return y(e, ye(e._zod.def, {
		get shape() {
			let n = {
				...e._zod.def.shape,
				...t._zod.def.shape
			};
			return ve(this, "shape", n), n;
		},
		get catchall() {
			return t._zod.def.catchall;
		},
		checks: t._zod.def.checks ?? []
	}));
}
function Ie(e, t, n) {
	let r = t._zod.def.checks;
	if (r && r.length > 0) throw Error(".partial() cannot be used on object schemas containing refinements");
	return y(t, ye(t._zod.def, {
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
			return ve(this, "shape", i), i;
		},
		checks: []
	}));
}
function Le(e, t, n) {
	return y(t, ye(t._zod.def, { get shape() {
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
		return ve(this, "shape", i), i;
	} }));
}
function Re(e, t = 0) {
	if (e.aborted === !0) return !0;
	for (let n = t; n < e.issues.length; n++) if (e.issues[n]?.continue !== !0) return !0;
	return !1;
}
function ze(e, t = 0) {
	if (e.aborted === !0) return !0;
	for (let n = t; n < e.issues.length; n++) if (e.issues[n]?.continue === !1) return !0;
	return !1;
}
function Be(e, t) {
	return t.map((t) => {
		var n;
		return (n = t).path ?? (n.path = []), t.path.unshift(e), t;
	});
}
function Ve(e) {
	return typeof e == "string" ? e : e?.message;
}
function x(e, t, n) {
	let r = e.message ? e.message : Ve(e.inst?._zod.def?.error?.(e)) ?? Ve(t?.error?.(e)) ?? Ve(n.customError?.(e)) ?? Ve(n.localeError?.(e)) ?? "Invalid input", { inst: i, continue: a, input: o, ...s } = e;
	return s.path ??= [], s.message = r, t?.reportInput && (s.input = o), s;
}
function He(e) {
	return Array.isArray(e) ? "array" : typeof e == "string" ? "string" : "unknown";
}
function Ue(...e) {
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
var We = (e, t) => {
	e.name = "$ZodError", Object.defineProperty(e, "_zod", {
		value: e._zod,
		enumerable: !1
	}), Object.defineProperty(e, "issues", {
		value: t,
		enumerable: !1
	}), e.message = JSON.stringify(t, fe, 2), Object.defineProperty(e, "toString", {
		value: () => e.message,
		enumerable: !1
	});
}, Ge = g("$ZodError", We), Ke = g("$ZodError", We, { Parent: Error });
function qe(e, t = (e) => e.message) {
	let n = {}, r = [];
	for (let i of e.issues) i.path.length > 0 ? (n[i.path[0]] = n[i.path[0]] || [], n[i.path[0]].push(t(i))) : r.push(t(i));
	return {
		formErrors: r,
		fieldErrors: n
	};
}
function Je(e, t = (e) => e.message) {
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
var Ye = (e) => (t, n, r, i) => {
	let a = r ? {
		...r,
		async: !1
	} : { async: !1 }, o = t._zod.run({
		value: n,
		issues: []
	}, a);
	if (o instanceof Promise) throw new ce();
	if (o.issues.length) {
		let t = new ((i?.Err) ?? e)(o.issues.map((e) => x(e, a, _())));
		throw Se(t, i?.callee), t;
	}
	return o.value;
}, Xe = (e) => async (t, n, r, i) => {
	let a = r ? {
		...r,
		async: !0
	} : { async: !0 }, o = t._zod.run({
		value: n,
		issues: []
	}, a);
	if (o instanceof Promise && (o = await o), o.issues.length) {
		let t = new ((i?.Err) ?? e)(o.issues.map((e) => x(e, a, _())));
		throw Se(t, i?.callee), t;
	}
	return o.value;
}, Ze = (e) => (t, n, r) => {
	let i = r ? {
		...r,
		async: !1
	} : { async: !1 }, a = t._zod.run({
		value: n,
		issues: []
	}, i);
	if (a instanceof Promise) throw new ce();
	return a.issues.length ? {
		success: !1,
		error: new (e ?? Ge)(a.issues.map((e) => x(e, i, _())))
	} : {
		success: !0,
		data: a.value
	};
}, Qe = /* @__PURE__*/ Ze(Ke), $e = (e) => async (t, n, r) => {
	let i = r ? {
		...r,
		async: !0
	} : { async: !0 }, a = t._zod.run({
		value: n,
		issues: []
	}, i);
	return a instanceof Promise && (a = await a), a.issues.length ? {
		success: !1,
		error: new e(a.issues.map((e) => x(e, i, _())))
	} : {
		success: !0,
		data: a.value
	};
}, et = /* @__PURE__*/ $e(Ke), tt = (e) => (t, n, r) => {
	let i = r ? {
		...r,
		direction: "backward"
	} : { direction: "backward" };
	return Ye(e)(t, n, i);
}, nt = (e) => (t, n, r) => Ye(e)(t, n, r), rt = (e) => async (t, n, r) => {
	let i = r ? {
		...r,
		direction: "backward"
	} : { direction: "backward" };
	return Xe(e)(t, n, i);
}, it = (e) => async (t, n, r) => Xe(e)(t, n, r), at = (e) => (t, n, r) => {
	let i = r ? {
		...r,
		direction: "backward"
	} : { direction: "backward" };
	return Ze(e)(t, n, i);
}, ot = (e) => (t, n, r) => Ze(e)(t, n, r), st = (e) => async (t, n, r) => {
	let i = r ? {
		...r,
		direction: "backward"
	} : { direction: "backward" };
	return $e(e)(t, n, i);
}, ct = (e) => async (t, n, r) => $e(e)(t, n, r), lt = /^[cC][0-9a-z]{6,}$/, ut = /^[0-9a-z]+$/, dt = /^[0-9A-HJKMNP-TV-Za-hjkmnp-tv-z]{26}$/, ft = /^[0-9a-vA-V]{20}$/, pt = /^[A-Za-z0-9]{27}$/, mt = /^[a-zA-Z0-9_-]{21}$/, ht = /^P(?:(\d+W)|(?!.*W)(?=\d|T\d)(\d+Y)?(\d+M)?(\d+D)?(T(?=\d)(\d+H)?(\d+M)?(\d+([.,]\d+)?S)?)?)$/, gt = /^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$/, _t = (e) => e ? RegExp(`^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-${e}[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12})$`) : /^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$/, vt = /^(?!\.)(?!.*\.\.)([A-Za-z0-9_'+\-\.]*)[A-Za-z0-9_+-]@([A-Za-z0-9][A-Za-z0-9\-]*\.)+[A-Za-z]{2,}$/, yt = "^(\\p{Extended_Pictographic}|\\p{Emoji_Component})+$";
function bt() {
	return new RegExp(yt, "u");
}
var xt = /^(?:(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])\.){3}(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])$/, St = /^(([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:))$/, Ct = /^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])\/([0-9]|[1-2][0-9]|3[0-2])$/, wt = /^(([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|::|([0-9a-fA-F]{1,4})?::([0-9a-fA-F]{1,4}:?){0,6})\/(12[0-8]|1[01][0-9]|[1-9]?[0-9])$/, Tt = /^$|^(?:[0-9a-zA-Z+/]{4})*(?:(?:[0-9a-zA-Z+/]{2}==)|(?:[0-9a-zA-Z+/]{3}=))?$/, Et = /^[A-Za-z0-9_-]*$/, Dt = /^https?$/, Ot = /^\+[1-9]\d{6,14}$/, kt = "(?:(?:\\d\\d[2468][048]|\\d\\d[13579][26]|\\d\\d0[48]|[02468][048]00|[13579][26]00)-02-29|\\d{4}-(?:(?:0[13578]|1[02])-(?:0[1-9]|[12]\\d|3[01])|(?:0[469]|11)-(?:0[1-9]|[12]\\d|30)|(?:02)-(?:0[1-9]|1\\d|2[0-8])))", At = /*@__PURE__*/ RegExp(`^${kt}$`);
function jt(e) {
	let t = "(?:[01]\\d|2[0-3]):[0-5]\\d";
	return typeof e.precision == "number" ? e.precision === -1 ? `${t}` : e.precision === 0 ? `${t}:[0-5]\\d` : `${t}:[0-5]\\d\\.\\d{${e.precision}}` : `${t}(?::[0-5]\\d(?:\\.\\d+)?)?`;
}
function Mt(e) {
	return RegExp(`^${jt(e)}$`);
}
function Nt(e) {
	let t = jt({ precision: e.precision }), n = ["Z"];
	e.local && n.push(""), e.offset && n.push("([+-](?:[01]\\d|2[0-3]):[0-5]\\d)");
	let r = `${t}(?:${n.join("|")})`;
	return RegExp(`^${kt}T(?:${r})$`);
}
var Pt = (e) => {
	let t = e ? `[\\s\\S]{${e?.minimum ?? 0},${e?.maximum ?? ""}}` : "[\\s\\S]*";
	return RegExp(`^${t}$`);
}, Ft = /^-?\d+$/, It = /^-?\d+(?:\.\d+)?$/, Lt = /^(?:true|false)$/i, Rt = /^[^A-Z]*$/, zt = /^[^a-z]*$/, S = /*@__PURE__*/ g("$ZodCheck", (e, t) => {
	var n;
	e._zod ??= {}, e._zod.def = t, (n = e._zod).onattach ?? (n.onattach = []);
}), Bt = {
	number: "number",
	bigint: "bigint",
	object: "date"
}, Vt = /*@__PURE__*/ g("$ZodCheckLessThan", (e, t) => {
	S.init(e, t);
	let n = Bt[typeof t.value];
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
}), Ht = /*@__PURE__*/ g("$ZodCheckGreaterThan", (e, t) => {
	S.init(e, t);
	let n = Bt[typeof t.value];
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
}), Ut = /*@__PURE__*/ g("$ZodCheckMultipleOf", (e, t) => {
	S.init(e, t), e._zod.onattach.push((e) => {
		var n;
		(n = e._zod.bag).multipleOf ?? (n.multipleOf = t.value);
	}), e._zod.check = (n) => {
		if (typeof n.value != typeof t.value) throw Error("Cannot mix number and bigint in multiple_of check.");
		(typeof n.value == "bigint" ? n.value % t.value === BigInt(0) : ge(n.value, t.value) === 0) || n.issues.push({
			origin: typeof n.value,
			code: "not_multiple_of",
			divisor: t.value,
			input: n.value,
			inst: e,
			continue: !t.abort
		});
	};
}), Wt = /*@__PURE__*/ g("$ZodCheckNumberFormat", (e, t) => {
	S.init(e, t), t.format = t.format || "float64";
	let n = t.format?.includes("int"), r = n ? "int" : "number", [i, a] = Ae[t.format];
	e._zod.onattach.push((e) => {
		let r = e._zod.bag;
		r.format = t.format, r.minimum = i, r.maximum = a, n && (r.pattern = Ft);
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
}), Gt = /*@__PURE__*/ g("$ZodCheckMaxLength", (e, t) => {
	var n;
	S.init(e, t), (n = e._zod.def).when ?? (n.when = (e) => {
		let t = e.value;
		return !me(t) && t.length !== void 0;
	}), e._zod.onattach.push((e) => {
		let n = e._zod.bag.maximum ?? Infinity;
		t.maximum < n && (e._zod.bag.maximum = t.maximum);
	}), e._zod.check = (n) => {
		let r = n.value;
		if (r.length <= t.maximum) return;
		let i = He(r);
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
}), Kt = /*@__PURE__*/ g("$ZodCheckMinLength", (e, t) => {
	var n;
	S.init(e, t), (n = e._zod.def).when ?? (n.when = (e) => {
		let t = e.value;
		return !me(t) && t.length !== void 0;
	}), e._zod.onattach.push((e) => {
		let n = e._zod.bag.minimum ?? -Infinity;
		t.minimum > n && (e._zod.bag.minimum = t.minimum);
	}), e._zod.check = (n) => {
		let r = n.value;
		if (r.length >= t.minimum) return;
		let i = He(r);
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
}), qt = /*@__PURE__*/ g("$ZodCheckLengthEquals", (e, t) => {
	var n;
	S.init(e, t), (n = e._zod.def).when ?? (n.when = (e) => {
		let t = e.value;
		return !me(t) && t.length !== void 0;
	}), e._zod.onattach.push((e) => {
		let n = e._zod.bag;
		n.minimum = t.length, n.maximum = t.length, n.length = t.length;
	}), e._zod.check = (n) => {
		let r = n.value, i = r.length;
		if (i === t.length) return;
		let a = He(r), o = i > t.length;
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
}), Jt = /*@__PURE__*/ g("$ZodCheckStringFormat", (e, t) => {
	var n, r;
	S.init(e, t), e._zod.onattach.push((e) => {
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
}), Yt = /*@__PURE__*/ g("$ZodCheckRegex", (e, t) => {
	Jt.init(e, t), e._zod.check = (n) => {
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
}), Xt = /*@__PURE__*/ g("$ZodCheckLowerCase", (e, t) => {
	t.pattern ??= Rt, Jt.init(e, t);
}), Zt = /*@__PURE__*/ g("$ZodCheckUpperCase", (e, t) => {
	t.pattern ??= zt, Jt.init(e, t);
}), Qt = /*@__PURE__*/ g("$ZodCheckIncludes", (e, t) => {
	S.init(e, t);
	let n = Oe(t.includes), r = new RegExp(typeof t.position == "number" ? `^.{${t.position}}${n}` : n);
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
}), $t = /*@__PURE__*/ g("$ZodCheckStartsWith", (e, t) => {
	S.init(e, t);
	let n = RegExp(`^${Oe(t.prefix)}.*`);
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
}), en = /*@__PURE__*/ g("$ZodCheckEndsWith", (e, t) => {
	S.init(e, t);
	let n = RegExp(`.*${Oe(t.suffix)}$`);
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
}), tn = /*@__PURE__*/ g("$ZodCheckOverwrite", (e, t) => {
	S.init(e, t), e._zod.check = (e) => {
		e.value = t.tx(e.value);
	};
}), nn = class {
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
}, rn = {
	major: 4,
	minor: 4,
	patch: 3
}, C = /*@__PURE__*/ g("$ZodType", (e, t) => {
	var n;
	e ??= {}, e._zod.def = t, e._zod.bag = e._zod.bag || {}, e._zod.version = rn;
	let r = [...e._zod.def.checks ?? []];
	e._zod.traits.has("$ZodCheck") && r.unshift(e);
	for (let t of r) for (let n of t._zod.onattach) n(e);
	if (r.length === 0) (n = e._zod).deferred ?? (n.deferred = []), e._zod.deferred?.push(() => {
		e._zod.run = e._zod.parse;
	});
	else {
		let t = (e, t, n) => {
			let r = Re(e), i;
			for (let a of t) {
				if (a._zod.def.when) {
					if (ze(e) || !a._zod.def.when(e)) continue;
				} else if (r) continue;
				let t = e.issues.length, o = a._zod.check(e);
				if (o instanceof Promise && n?.async === !1) throw new ce();
				if (i || o instanceof Promise) i = (i ?? Promise.resolve()).then(async () => {
					await o, e.issues.length !== t && (r ||= Re(e, t));
				});
				else {
					if (e.issues.length === t) continue;
					r ||= Re(e, t);
				}
			}
			return i ? i.then(() => e) : e;
		}, n = (n, i, a) => {
			if (Re(n)) return n.aborted = !0, n;
			let o = t(i, r, a);
			if (o instanceof Promise) {
				if (a.async === !1) throw new ce();
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
				if (a.async === !1) throw new ce();
				return o.then((e) => t(e, r, a));
			}
			return t(o, r, a);
		};
	}
	v(e, "~standard", () => ({
		validate: (t) => {
			try {
				let n = Qe(e, t);
				return n.success ? { value: n.data } : { issues: n.error?.issues };
			} catch {
				return et(e, t).then((e) => e.success ? { value: e.data } : { issues: e.error?.issues });
			}
		},
		vendor: "zod",
		version: 1
	}));
}), an = /*@__PURE__*/ g("$ZodString", (e, t) => {
	C.init(e, t), e._zod.pattern = [...e?._zod.bag?.patterns ?? []].pop() ?? Pt(e._zod.bag), e._zod.parse = (n, r) => {
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
}), w = /*@__PURE__*/ g("$ZodStringFormat", (e, t) => {
	Jt.init(e, t), an.init(e, t);
}), on = /*@__PURE__*/ g("$ZodGUID", (e, t) => {
	t.pattern ??= gt, w.init(e, t);
}), sn = /*@__PURE__*/ g("$ZodUUID", (e, t) => {
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
		t.pattern ??= _t(e);
	} else t.pattern ??= _t();
	w.init(e, t);
}), cn = /*@__PURE__*/ g("$ZodEmail", (e, t) => {
	t.pattern ??= vt, w.init(e, t);
}), ln = /*@__PURE__*/ g("$ZodURL", (e, t) => {
	w.init(e, t), e._zod.check = (n) => {
		try {
			let r = n.value.trim();
			if (!t.normalize && t.protocol?.source === Dt.source && !/^https?:\/\//i.test(r)) {
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
}), un = /*@__PURE__*/ g("$ZodEmoji", (e, t) => {
	t.pattern ??= bt(), w.init(e, t);
}), dn = /*@__PURE__*/ g("$ZodNanoID", (e, t) => {
	t.pattern ??= mt, w.init(e, t);
}), fn = /*@__PURE__*/ g("$ZodCUID", (e, t) => {
	t.pattern ??= lt, w.init(e, t);
}), pn = /*@__PURE__*/ g("$ZodCUID2", (e, t) => {
	t.pattern ??= ut, w.init(e, t);
}), mn = /*@__PURE__*/ g("$ZodULID", (e, t) => {
	t.pattern ??= dt, w.init(e, t);
}), hn = /*@__PURE__*/ g("$ZodXID", (e, t) => {
	t.pattern ??= ft, w.init(e, t);
}), gn = /*@__PURE__*/ g("$ZodKSUID", (e, t) => {
	t.pattern ??= pt, w.init(e, t);
}), _n = /*@__PURE__*/ g("$ZodISODateTime", (e, t) => {
	t.pattern ??= Nt(t), w.init(e, t);
}), vn = /*@__PURE__*/ g("$ZodISODate", (e, t) => {
	t.pattern ??= At, w.init(e, t);
}), yn = /*@__PURE__*/ g("$ZodISOTime", (e, t) => {
	t.pattern ??= Mt(t), w.init(e, t);
}), bn = /*@__PURE__*/ g("$ZodISODuration", (e, t) => {
	t.pattern ??= ht, w.init(e, t);
}), xn = /*@__PURE__*/ g("$ZodIPv4", (e, t) => {
	t.pattern ??= xt, w.init(e, t), e._zod.bag.format = "ipv4";
}), Sn = /*@__PURE__*/ g("$ZodIPv6", (e, t) => {
	t.pattern ??= St, w.init(e, t), e._zod.bag.format = "ipv6", e._zod.check = (n) => {
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
}), Cn = /*@__PURE__*/ g("$ZodCIDRv4", (e, t) => {
	t.pattern ??= Ct, w.init(e, t);
}), wn = /*@__PURE__*/ g("$ZodCIDRv6", (e, t) => {
	t.pattern ??= wt, w.init(e, t), e._zod.check = (n) => {
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
function Tn(e) {
	if (e === "") return !0;
	if (/\s/.test(e) || e.length % 4 != 0) return !1;
	try {
		return atob(e), !0;
	} catch {
		return !1;
	}
}
var En = /*@__PURE__*/ g("$ZodBase64", (e, t) => {
	t.pattern ??= Tt, w.init(e, t), e._zod.bag.contentEncoding = "base64", e._zod.check = (n) => {
		Tn(n.value) || n.issues.push({
			code: "invalid_format",
			format: "base64",
			input: n.value,
			inst: e,
			continue: !t.abort
		});
	};
});
function Dn(e) {
	if (!Et.test(e)) return !1;
	let t = e.replace(/[-_]/g, (e) => e === "-" ? "+" : "/");
	return Tn(t.padEnd(Math.ceil(t.length / 4) * 4, "="));
}
var On = /*@__PURE__*/ g("$ZodBase64URL", (e, t) => {
	t.pattern ??= Et, w.init(e, t), e._zod.bag.contentEncoding = "base64url", e._zod.check = (n) => {
		Dn(n.value) || n.issues.push({
			code: "invalid_format",
			format: "base64url",
			input: n.value,
			inst: e,
			continue: !t.abort
		});
	};
}), kn = /*@__PURE__*/ g("$ZodE164", (e, t) => {
	t.pattern ??= Ot, w.init(e, t);
});
function An(e, t = null) {
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
var jn = /*@__PURE__*/ g("$ZodJWT", (e, t) => {
	w.init(e, t), e._zod.check = (n) => {
		An(n.value, t.alg) || n.issues.push({
			code: "invalid_format",
			format: "jwt",
			input: n.value,
			inst: e,
			continue: !t.abort
		});
	};
}), Mn = /*@__PURE__*/ g("$ZodNumber", (e, t) => {
	C.init(e, t), e._zod.pattern = e._zod.bag.pattern ?? It, e._zod.parse = (n, r) => {
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
}), Nn = /*@__PURE__*/ g("$ZodNumberFormat", (e, t) => {
	Wt.init(e, t), Mn.init(e, t);
}), Pn = /*@__PURE__*/ g("$ZodBoolean", (e, t) => {
	C.init(e, t), e._zod.pattern = Lt, e._zod.parse = (n, r) => {
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
}), Fn = /*@__PURE__*/ g("$ZodUnknown", (e, t) => {
	C.init(e, t), e._zod.parse = (e) => e;
}), In = /*@__PURE__*/ g("$ZodNever", (e, t) => {
	C.init(e, t), e._zod.parse = (t, n) => (t.issues.push({
		expected: "never",
		code: "invalid_type",
		input: t.value,
		inst: e
	}), t);
});
function Ln(e, t, n) {
	e.issues.length && t.issues.push(...Be(n, e.issues)), t.value[n] = e.value;
}
var Rn = /*@__PURE__*/ g("$ZodArray", (e, t) => {
	C.init(e, t), e._zod.parse = (n, r) => {
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
			s instanceof Promise ? a.push(s.then((t) => Ln(t, n, e))) : Ln(s, n, e);
		}
		return a.length ? Promise.all(a).then(() => n) : n;
	};
});
function zn(e, t, n, r, i, a) {
	let o = n in r;
	if (e.issues.length) {
		if (i && a && !o) return;
		t.issues.push(...Be(n, e.issues));
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
function Bn(e) {
	let t = Object.keys(e.shape);
	for (let n of t) if (!e.shape?.[n]?._zod?.traits?.has("$ZodType")) throw Error(`Invalid element at key "${n}": expected a Zod schema`);
	let n = ke(e.shape);
	return {
		...e,
		keys: t,
		keySet: new Set(t),
		numKeys: t.length,
		optionalKeys: new Set(n)
	};
}
function Vn(e, t, n, r, i, a) {
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
		a instanceof Promise ? e.push(a.then((e) => zn(e, n, i, t, u, d))) : zn(a, n, i, t, u, d);
	}
	return o.length && n.issues.push({
		code: "unrecognized_keys",
		keys: o,
		input: t,
		inst: a
	}), e.length ? Promise.all(e).then(() => n) : n;
}
var Hn = /*@__PURE__*/ g("$ZodObject", (e, t) => {
	if (C.init(e, t), !Object.getOwnPropertyDescriptor(t, "shape")?.get) {
		let e = t.shape;
		Object.defineProperty(t, "shape", { get: () => {
			let n = { ...e };
			return Object.defineProperty(t, "shape", { value: n }), n;
		} });
	}
	let n = pe(() => Bn(t));
	v(e._zod, "propValues", () => {
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
	let r = Ce, i = t.catchall, a;
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
			a instanceof Promise ? c.push(a.then((n) => zn(n, t, e, s, r, i))) : zn(a, t, e, s, r, i);
		}
		return i ? Vn(c, s, t, o, n.value, e) : c.length ? Promise.all(c).then(() => t) : t;
	};
}), Un = /*@__PURE__*/ g("$ZodObjectJIT", (e, t) => {
	Hn.init(e, t);
	let n = e._zod.parse, r = pe(() => Bn(t)), i = (e) => {
		let t = new nn([
			"shape",
			"payload",
			"ctx"
		]), n = r.value, i = (e) => {
			let t = be(e);
			return `shape[${t}]._zod.run({ value: input[${t}], issues: [] }, ctx)`;
		};
		t.write("const input = payload.value;");
		let a = Object.create(null), o = 0;
		for (let e of n.keys) a[e] = `key_${o++}`;
		t.write("const newResult = {};");
		for (let r of n.keys) {
			let n = a[r], o = be(r), s = e[r], c = s?._zod?.optin === "optional", l = s?._zod?.optout === "optional";
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
	}, a, o = Ce, s = !ue.jitless, c = s && we.value, l = t.catchall, u;
	e._zod.parse = (d, f) => {
		u ??= r.value;
		let p = d.value;
		return o(p) ? s && c && f?.async === !1 && f.jitless !== !0 ? (a ||= i(t.shape), d = a(d, f), l ? Vn([], p, d, f, u, e) : d) : n(d, f) : (d.issues.push({
			expected: "object",
			code: "invalid_type",
			input: p,
			inst: e
		}), d);
	};
});
function Wn(e, t, n, r) {
	for (let n of e) if (n.issues.length === 0) return t.value = n.value, t;
	let i = e.filter((e) => !Re(e));
	return i.length === 1 ? (t.value = i[0].value, i[0]) : (t.issues.push({
		code: "invalid_union",
		input: t.value,
		inst: n,
		errors: e.map((e) => e.issues.map((e) => x(e, r, _())))
	}), t);
}
var Gn = /*@__PURE__*/ g("$ZodUnion", (e, t) => {
	C.init(e, t), v(e._zod, "optin", () => t.options.some((e) => e._zod.optin === "optional") ? "optional" : void 0), v(e._zod, "optout", () => t.options.some((e) => e._zod.optout === "optional") ? "optional" : void 0), v(e._zod, "values", () => {
		if (t.options.every((e) => e._zod.values)) return new Set(t.options.flatMap((e) => Array.from(e._zod.values)));
	}), v(e._zod, "pattern", () => {
		if (t.options.every((e) => e._zod.pattern)) {
			let e = t.options.map((e) => e._zod.pattern);
			return RegExp(`^(${e.map((e) => he(e.source)).join("|")})$`);
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
		return a ? Promise.all(o).then((t) => Wn(t, r, e, i)) : Wn(o, r, e, i);
	};
}), Kn = /*@__PURE__*/ g("$ZodIntersection", (e, t) => {
	C.init(e, t), e._zod.parse = (e, n) => {
		let r = e.value, i = t.left._zod.run({
			value: r,
			issues: []
		}, n), a = t.right._zod.run({
			value: r,
			issues: []
		}, n);
		return i instanceof Promise || a instanceof Promise ? Promise.all([i, a]).then(([t, n]) => Jn(e, t, n)) : Jn(e, i, a);
	};
});
function qn(e, t) {
	if (e === t || e instanceof Date && t instanceof Date && +e == +t) return {
		valid: !0,
		data: e
	};
	if (Te(e) && Te(t)) {
		let n = Object.keys(t), r = Object.keys(e).filter((e) => n.indexOf(e) !== -1), i = {
			...e,
			...t
		};
		for (let n of r) {
			let r = qn(e[n], t[n]);
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
			let i = e[r], a = t[r], o = qn(i, a);
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
function Jn(e, t, n) {
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
	}), Re(e)) return e;
	let o = qn(t.value, n.value);
	if (!o.valid) throw Error(`Unmergable intersection. Error path: ${JSON.stringify(o.mergeErrorPath)}`);
	return e.value = o.data, e;
}
var Yn = /*@__PURE__*/ g("$ZodRecord", (e, t) => {
	C.init(e, t), e._zod.parse = (n, r) => {
		let i = n.value;
		if (!Te(i)) return n.issues.push({
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
						issues: o.issues.map((e) => x(e, r, _())),
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
					e.issues.length && n.issues.push(...Be(c, e.issues)), n.value[l] = e.value;
				})) : (u.issues.length && n.issues.push(...Be(c, u.issues)), n.value[l] = u.value);
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
				if (typeof o == "string" && It.test(o) && s.issues.length) {
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
						issues: s.issues.map((e) => x(e, r, _())),
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
					e.issues.length && n.issues.push(...Be(o, e.issues)), n.value[s.value] = e.value;
				})) : (c.issues.length && n.issues.push(...Be(o, c.issues)), n.value[s.value] = c.value);
			}
		}
		return a.length ? Promise.all(a).then(() => n) : n;
	};
}), Xn = /*@__PURE__*/ g("$ZodEnum", (e, t) => {
	C.init(e, t);
	let n = de(t.entries), r = new Set(n);
	e._zod.values = r, e._zod.pattern = RegExp(`^(${n.filter((e) => De.has(typeof e)).map((e) => typeof e == "string" ? Oe(e) : e.toString()).join("|")})$`), e._zod.parse = (t, i) => {
		let a = t.value;
		return r.has(a) || t.issues.push({
			code: "invalid_value",
			values: n,
			input: a,
			inst: e
		}), t;
	};
}), Zn = /*@__PURE__*/ g("$ZodLiteral", (e, t) => {
	if (C.init(e, t), t.values.length === 0) throw Error("Cannot create literal schema with no valid values");
	let n = new Set(t.values);
	e._zod.values = n, e._zod.pattern = RegExp(`^(${t.values.map((e) => typeof e == "string" ? Oe(e) : e ? Oe(e.toString()) : String(e)).join("|")})$`), e._zod.parse = (r, i) => {
		let a = r.value;
		return n.has(a) || r.issues.push({
			code: "invalid_value",
			values: t.values,
			input: a,
			inst: e
		}), r;
	};
}), Qn = /*@__PURE__*/ g("$ZodTransform", (e, t) => {
	C.init(e, t), e._zod.optin = "optional", e._zod.parse = (n, r) => {
		if (r.direction === "backward") throw new le(e.constructor.name);
		let i = t.transform(n.value, n);
		if (r.async) return (i instanceof Promise ? i : Promise.resolve(i)).then((e) => (n.value = e, n.fallback = !0, n));
		if (i instanceof Promise) throw new ce();
		return n.value = i, n.fallback = !0, n;
	};
});
function $n(e, t) {
	return t === void 0 && (e.issues.length || e.fallback) ? {
		issues: [],
		value: void 0
	} : e;
}
var er = /*@__PURE__*/ g("$ZodOptional", (e, t) => {
	C.init(e, t), e._zod.optin = "optional", e._zod.optout = "optional", v(e._zod, "values", () => t.innerType._zod.values ? /* @__PURE__ */ new Set([...t.innerType._zod.values, void 0]) : void 0), v(e._zod, "pattern", () => {
		let e = t.innerType._zod.pattern;
		return e ? RegExp(`^(${he(e.source)})?$`) : void 0;
	}), e._zod.parse = (e, n) => {
		if (t.innerType._zod.optin === "optional") {
			let r = e.value, i = t.innerType._zod.run(e, n);
			return i instanceof Promise ? i.then((e) => $n(e, r)) : $n(i, r);
		}
		return e.value === void 0 ? e : t.innerType._zod.run(e, n);
	};
}), tr = /*@__PURE__*/ g("$ZodExactOptional", (e, t) => {
	er.init(e, t), v(e._zod, "values", () => t.innerType._zod.values), v(e._zod, "pattern", () => t.innerType._zod.pattern), e._zod.parse = (e, n) => t.innerType._zod.run(e, n);
}), nr = /*@__PURE__*/ g("$ZodNullable", (e, t) => {
	C.init(e, t), v(e._zod, "optin", () => t.innerType._zod.optin), v(e._zod, "optout", () => t.innerType._zod.optout), v(e._zod, "pattern", () => {
		let e = t.innerType._zod.pattern;
		return e ? RegExp(`^(${he(e.source)}|null)$`) : void 0;
	}), v(e._zod, "values", () => t.innerType._zod.values ? /* @__PURE__ */ new Set([...t.innerType._zod.values, null]) : void 0), e._zod.parse = (e, n) => e.value === null ? e : t.innerType._zod.run(e, n);
}), rr = /*@__PURE__*/ g("$ZodDefault", (e, t) => {
	C.init(e, t), e._zod.optin = "optional", v(e._zod, "values", () => t.innerType._zod.values), e._zod.parse = (e, n) => {
		if (n.direction === "backward") return t.innerType._zod.run(e, n);
		if (e.value === void 0) return e.value = t.defaultValue, e;
		let r = t.innerType._zod.run(e, n);
		return r instanceof Promise ? r.then((e) => ir(e, t)) : ir(r, t);
	};
});
function ir(e, t) {
	return e.value === void 0 && (e.value = t.defaultValue), e;
}
var ar = /*@__PURE__*/ g("$ZodPrefault", (e, t) => {
	C.init(e, t), e._zod.optin = "optional", v(e._zod, "values", () => t.innerType._zod.values), e._zod.parse = (e, n) => (n.direction === "backward" || e.value === void 0 && (e.value = t.defaultValue), t.innerType._zod.run(e, n));
}), or = /*@__PURE__*/ g("$ZodNonOptional", (e, t) => {
	C.init(e, t), v(e._zod, "values", () => {
		let e = t.innerType._zod.values;
		return e ? new Set([...e].filter((e) => e !== void 0)) : void 0;
	}), e._zod.parse = (n, r) => {
		let i = t.innerType._zod.run(n, r);
		return i instanceof Promise ? i.then((t) => sr(t, e)) : sr(i, e);
	};
});
function sr(e, t) {
	return !e.issues.length && e.value === void 0 && e.issues.push({
		code: "invalid_type",
		expected: "nonoptional",
		input: e.value,
		inst: t
	}), e;
}
var cr = /*@__PURE__*/ g("$ZodCatch", (e, t) => {
	C.init(e, t), e._zod.optin = "optional", v(e._zod, "optout", () => t.innerType._zod.optout), v(e._zod, "values", () => t.innerType._zod.values), e._zod.parse = (e, n) => {
		if (n.direction === "backward") return t.innerType._zod.run(e, n);
		let r = t.innerType._zod.run(e, n);
		return r instanceof Promise ? r.then((r) => (e.value = r.value, r.issues.length && (e.value = t.catchValue({
			...e,
			error: { issues: r.issues.map((e) => x(e, n, _())) },
			input: e.value
		}), e.issues = [], e.fallback = !0), e)) : (e.value = r.value, r.issues.length && (e.value = t.catchValue({
			...e,
			error: { issues: r.issues.map((e) => x(e, n, _())) },
			input: e.value
		}), e.issues = [], e.fallback = !0), e);
	};
}), lr = /*@__PURE__*/ g("$ZodPipe", (e, t) => {
	C.init(e, t), v(e._zod, "values", () => t.in._zod.values), v(e._zod, "optin", () => t.in._zod.optin), v(e._zod, "optout", () => t.out._zod.optout), v(e._zod, "propValues", () => t.in._zod.propValues), e._zod.parse = (e, n) => {
		if (n.direction === "backward") {
			let r = t.out._zod.run(e, n);
			return r instanceof Promise ? r.then((e) => ur(e, t.in, n)) : ur(r, t.in, n);
		}
		let r = t.in._zod.run(e, n);
		return r instanceof Promise ? r.then((e) => ur(e, t.out, n)) : ur(r, t.out, n);
	};
});
function ur(e, t, n) {
	return e.issues.length ? (e.aborted = !0, e) : t._zod.run({
		value: e.value,
		issues: e.issues,
		fallback: e.fallback
	}, n);
}
var dr = /*@__PURE__*/ g("$ZodReadonly", (e, t) => {
	C.init(e, t), v(e._zod, "propValues", () => t.innerType._zod.propValues), v(e._zod, "values", () => t.innerType._zod.values), v(e._zod, "optin", () => t.innerType?._zod?.optin), v(e._zod, "optout", () => t.innerType?._zod?.optout), e._zod.parse = (e, n) => {
		if (n.direction === "backward") return t.innerType._zod.run(e, n);
		let r = t.innerType._zod.run(e, n);
		return r instanceof Promise ? r.then(fr) : fr(r);
	};
});
function fr(e) {
	return e.value = Object.freeze(e.value), e;
}
var pr = /*@__PURE__*/ g("$ZodCustom", (e, t) => {
	S.init(e, t), C.init(e, t), e._zod.parse = (e, t) => e, e._zod.check = (n) => {
		let r = n.value, i = t.fn(r);
		if (i instanceof Promise) return i.then((t) => mr(t, n, r, e));
		mr(i, n, r, e);
	};
});
function mr(e, t, n, r) {
	if (!e) {
		let e = {
			code: "custom",
			input: n,
			inst: r,
			path: [...r._zod.def.path ?? []],
			continue: !r._zod.def.abort
		};
		r._zod.def.params && (e.params = r._zod.def.params), t.issues.push(Ue(e));
	}
}
//#endregion
//#region node_modules/.pnpm/zod@4.4.3/node_modules/zod/v4/core/registries.js
var hr, gr = class {
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
function _r() {
	return new gr();
}
(hr = globalThis).__zod_globalRegistry ?? (hr.__zod_globalRegistry = _r());
var vr = globalThis.__zod_globalRegistry;
//#endregion
//#region node_modules/.pnpm/zod@4.4.3/node_modules/zod/v4/core/api.js
// @__NO_SIDE_EFFECTS__
function yr(e, t) {
	return new e({
		type: "string",
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function br(e, t) {
	return new e({
		type: "string",
		format: "email",
		check: "string_format",
		abort: !1,
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function xr(e, t) {
	return new e({
		type: "string",
		format: "guid",
		check: "string_format",
		abort: !1,
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Sr(e, t) {
	return new e({
		type: "string",
		format: "uuid",
		check: "string_format",
		abort: !1,
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Cr(e, t) {
	return new e({
		type: "string",
		format: "uuid",
		check: "string_format",
		abort: !1,
		version: "v4",
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function wr(e, t) {
	return new e({
		type: "string",
		format: "uuid",
		check: "string_format",
		abort: !1,
		version: "v6",
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Tr(e, t) {
	return new e({
		type: "string",
		format: "uuid",
		check: "string_format",
		abort: !1,
		version: "v7",
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Er(e, t) {
	return new e({
		type: "string",
		format: "url",
		check: "string_format",
		abort: !1,
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Dr(e, t) {
	return new e({
		type: "string",
		format: "emoji",
		check: "string_format",
		abort: !1,
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Or(e, t) {
	return new e({
		type: "string",
		format: "nanoid",
		check: "string_format",
		abort: !1,
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function kr(e, t) {
	return new e({
		type: "string",
		format: "cuid",
		check: "string_format",
		abort: !1,
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Ar(e, t) {
	return new e({
		type: "string",
		format: "cuid2",
		check: "string_format",
		abort: !1,
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function jr(e, t) {
	return new e({
		type: "string",
		format: "ulid",
		check: "string_format",
		abort: !1,
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Mr(e, t) {
	return new e({
		type: "string",
		format: "xid",
		check: "string_format",
		abort: !1,
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Nr(e, t) {
	return new e({
		type: "string",
		format: "ksuid",
		check: "string_format",
		abort: !1,
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Pr(e, t) {
	return new e({
		type: "string",
		format: "ipv4",
		check: "string_format",
		abort: !1,
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Fr(e, t) {
	return new e({
		type: "string",
		format: "ipv6",
		check: "string_format",
		abort: !1,
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Ir(e, t) {
	return new e({
		type: "string",
		format: "cidrv4",
		check: "string_format",
		abort: !1,
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Lr(e, t) {
	return new e({
		type: "string",
		format: "cidrv6",
		check: "string_format",
		abort: !1,
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Rr(e, t) {
	return new e({
		type: "string",
		format: "base64",
		check: "string_format",
		abort: !1,
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function zr(e, t) {
	return new e({
		type: "string",
		format: "base64url",
		check: "string_format",
		abort: !1,
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Br(e, t) {
	return new e({
		type: "string",
		format: "e164",
		check: "string_format",
		abort: !1,
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Vr(e, t) {
	return new e({
		type: "string",
		format: "jwt",
		check: "string_format",
		abort: !1,
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Hr(e, t) {
	return new e({
		type: "string",
		format: "datetime",
		check: "string_format",
		offset: !1,
		local: !1,
		precision: null,
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Ur(e, t) {
	return new e({
		type: "string",
		format: "date",
		check: "string_format",
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Wr(e, t) {
	return new e({
		type: "string",
		format: "time",
		check: "string_format",
		precision: null,
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Gr(e, t) {
	return new e({
		type: "string",
		format: "duration",
		check: "string_format",
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Kr(e, t) {
	return new e({
		type: "number",
		checks: [],
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function qr(e, t) {
	return new e({
		type: "number",
		check: "number_format",
		abort: !1,
		format: "safeint",
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Jr(e, t) {
	return new e({
		type: "boolean",
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Yr(e) {
	return new e({ type: "unknown" });
}
// @__NO_SIDE_EFFECTS__
function Xr(e, t) {
	return new e({
		type: "never",
		...b(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Zr(e, t) {
	return new Vt({
		check: "less_than",
		...b(t),
		value: e,
		inclusive: !1
	});
}
// @__NO_SIDE_EFFECTS__
function Qr(e, t) {
	return new Vt({
		check: "less_than",
		...b(t),
		value: e,
		inclusive: !0
	});
}
// @__NO_SIDE_EFFECTS__
function $r(e, t) {
	return new Ht({
		check: "greater_than",
		...b(t),
		value: e,
		inclusive: !1
	});
}
// @__NO_SIDE_EFFECTS__
function ei(e, t) {
	return new Ht({
		check: "greater_than",
		...b(t),
		value: e,
		inclusive: !0
	});
}
// @__NO_SIDE_EFFECTS__
function ti(e, t) {
	return new Ut({
		check: "multiple_of",
		...b(t),
		value: e
	});
}
// @__NO_SIDE_EFFECTS__
function ni(e, t) {
	return new Gt({
		check: "max_length",
		...b(t),
		maximum: e
	});
}
// @__NO_SIDE_EFFECTS__
function ri(e, t) {
	return new Kt({
		check: "min_length",
		...b(t),
		minimum: e
	});
}
// @__NO_SIDE_EFFECTS__
function ii(e, t) {
	return new qt({
		check: "length_equals",
		...b(t),
		length: e
	});
}
// @__NO_SIDE_EFFECTS__
function ai(e, t) {
	return new Yt({
		check: "string_format",
		format: "regex",
		...b(t),
		pattern: e
	});
}
// @__NO_SIDE_EFFECTS__
function oi(e) {
	return new Xt({
		check: "string_format",
		format: "lowercase",
		...b(e)
	});
}
// @__NO_SIDE_EFFECTS__
function si(e) {
	return new Zt({
		check: "string_format",
		format: "uppercase",
		...b(e)
	});
}
// @__NO_SIDE_EFFECTS__
function ci(e, t) {
	return new Qt({
		check: "string_format",
		format: "includes",
		...b(t),
		includes: e
	});
}
// @__NO_SIDE_EFFECTS__
function li(e, t) {
	return new $t({
		check: "string_format",
		format: "starts_with",
		...b(t),
		prefix: e
	});
}
// @__NO_SIDE_EFFECTS__
function ui(e, t) {
	return new en({
		check: "string_format",
		format: "ends_with",
		...b(t),
		suffix: e
	});
}
// @__NO_SIDE_EFFECTS__
function di(e) {
	return new tn({
		check: "overwrite",
		tx: e
	});
}
// @__NO_SIDE_EFFECTS__
function fi(e) {
	return /* @__PURE__ */ di((t) => t.normalize(e));
}
// @__NO_SIDE_EFFECTS__
function pi() {
	return /* @__PURE__ */ di((e) => e.trim());
}
// @__NO_SIDE_EFFECTS__
function mi() {
	return /* @__PURE__ */ di((e) => e.toLowerCase());
}
// @__NO_SIDE_EFFECTS__
function hi() {
	return /* @__PURE__ */ di((e) => e.toUpperCase());
}
// @__NO_SIDE_EFFECTS__
function gi() {
	return /* @__PURE__ */ di((e) => xe(e));
}
// @__NO_SIDE_EFFECTS__
function _i(e, t, n) {
	return new e({
		type: "array",
		element: t,
		...b(n)
	});
}
// @__NO_SIDE_EFFECTS__
function vi(e, t, n) {
	return new e({
		type: "custom",
		check: "custom",
		fn: t,
		...b(n)
	});
}
// @__NO_SIDE_EFFECTS__
function yi(e, t) {
	let n = /* @__PURE__ */ bi((t) => (t.addIssue = (e) => {
		if (typeof e == "string") t.issues.push(Ue(e, t.value, n._zod.def));
		else {
			let r = e;
			r.fatal && (r.continue = !1), r.code ??= "custom", r.input ??= t.value, r.inst ??= n, r.continue ??= !n._zod.def.abort, t.issues.push(Ue(r));
		}
	}, e(t.value, t)), t);
	return n;
}
// @__NO_SIDE_EFFECTS__
function bi(e, t) {
	let n = new S({
		check: "custom",
		...b(t)
	});
	return n._zod.check = e, n;
}
//#endregion
//#region node_modules/.pnpm/zod@4.4.3/node_modules/zod/v4/core/to-json-schema.js
function xi(e) {
	let t = e?.target ?? "draft-2020-12";
	return t === "draft-4" && (t = "draft-04"), t === "draft-7" && (t = "draft-07"), {
		processors: e.processors ?? {},
		metadataRegistry: e?.metadata ?? vr,
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
function T(e, t, n = {
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
		a && (o.ref ||= a, T(a, t, r), t.seen.get(a).isParent = !0);
	}
	let c = t.metadataRegistry.get(e);
	return c && Object.assign(o.schema, c), t.io === "input" && E(e) && (delete o.schema.examples, delete o.schema.default), t.io === "input" && "_prefault" in o.schema && ((r = o.schema).default ?? (r.default = o.schema._prefault)), delete o.schema._prefault, t.seen.get(e).schema;
}
function Si(e, t) {
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
function Ci(e, t) {
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
					input: Ti(t, "input", e.processors),
					output: Ti(t, "output", e.processors)
				}
			},
			enumerable: !1,
			writable: !1
		}), n;
	} catch {
		throw Error("Error converting schema to JSON.");
	}
}
function E(e, t) {
	let n = t ?? { seen: /* @__PURE__ */ new Set() };
	if (n.seen.has(e)) return !1;
	n.seen.add(e);
	let r = e._zod.def;
	if (r.type === "transform") return !0;
	if (r.type === "array") return E(r.element, n);
	if (r.type === "set") return E(r.valueType, n);
	if (r.type === "lazy") return E(r.getter(), n);
	if (r.type === "promise" || r.type === "optional" || r.type === "nonoptional" || r.type === "nullable" || r.type === "readonly" || r.type === "default" || r.type === "prefault") return E(r.innerType, n);
	if (r.type === "intersection") return E(r.left, n) || E(r.right, n);
	if (r.type === "record" || r.type === "map") return E(r.keyType, n) || E(r.valueType, n);
	if (r.type === "pipe") return e._zod.traits.has("$ZodCodec") ? !0 : E(r.in, n) || E(r.out, n);
	if (r.type === "object") {
		for (let e in r.shape) if (E(r.shape[e], n)) return !0;
		return !1;
	}
	if (r.type === "union") {
		for (let e of r.options) if (E(e, n)) return !0;
		return !1;
	}
	if (r.type === "tuple") {
		for (let e of r.items) if (E(e, n)) return !0;
		return !!(r.rest && E(r.rest, n));
	}
	return !1;
}
var wi = (e, t = {}) => (n) => {
	let r = xi({
		...n,
		processors: t
	});
	return T(e, r), Si(r, e), Ci(r, e);
}, Ti = (e, t, n = {}) => (r) => {
	let { libraryOptions: i, target: a } = r ?? {}, o = xi({
		...i ?? {},
		target: a,
		io: t,
		processors: n
	});
	return T(e, o), Si(o, e), Ci(o, e);
}, Ei = {
	guid: "uuid",
	url: "uri",
	datetime: "date-time",
	json_string: "json-string",
	regex: ""
}, Di = (e, t, n, r) => {
	let i = n;
	i.type = "string";
	let { minimum: a, maximum: o, format: s, patterns: c, contentEncoding: l } = e._zod.bag;
	if (typeof a == "number" && (i.minLength = a), typeof o == "number" && (i.maxLength = o), s && (i.format = Ei[s] ?? s, i.format === "" && delete i.format, s === "time" && delete i.format), l && (i.contentEncoding = l), c && c.size > 0) {
		let e = [...c];
		e.length === 1 ? i.pattern = e[0].source : e.length > 1 && (i.allOf = [...e.map((e) => ({
			...t.target === "draft-07" || t.target === "draft-04" || t.target === "openapi-3.0" ? { type: "string" } : {},
			pattern: e.source
		}))]);
	}
}, Oi = (e, t, n, r) => {
	let i = n, { minimum: a, maximum: o, format: s, multipleOf: c, exclusiveMaximum: l, exclusiveMinimum: u } = e._zod.bag;
	i.type = typeof s == "string" && s.includes("int") ? "integer" : "number";
	let d = typeof u == "number" && u >= (a ?? -Infinity), f = typeof l == "number" && l <= (o ?? Infinity), p = t.target === "draft-04" || t.target === "openapi-3.0";
	d ? p ? (i.minimum = u, i.exclusiveMinimum = !0) : i.exclusiveMinimum = u : typeof a == "number" && (i.minimum = a), f ? p ? (i.maximum = l, i.exclusiveMaximum = !0) : i.exclusiveMaximum = l : typeof o == "number" && (i.maximum = o), typeof c == "number" && (i.multipleOf = c);
}, ki = (e, t, n, r) => {
	n.type = "boolean";
}, Ai = (e, t, n, r) => {
	n.not = {};
}, ji = (e, t, n, r) => {
	let i = e._zod.def, a = de(i.entries);
	a.every((e) => typeof e == "number") && (n.type = "number"), a.every((e) => typeof e == "string") && (n.type = "string"), n.enum = a;
}, Mi = (e, t, n, r) => {
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
}, Ni = (e, t, n, r) => {
	if (t.unrepresentable === "throw") throw Error("Custom types cannot be represented in JSON Schema");
}, Pi = (e, t, n, r) => {
	if (t.unrepresentable === "throw") throw Error("Transforms cannot be represented in JSON Schema");
}, Fi = (e, t, n, r) => {
	let i = n, a = e._zod.def, { minimum: o, maximum: s } = e._zod.bag;
	typeof o == "number" && (i.minItems = o), typeof s == "number" && (i.maxItems = s), i.type = "array", i.items = T(a.element, t, {
		...r,
		path: [...r.path, "items"]
	});
}, Ii = (e, t, n, r) => {
	let i = n, a = e._zod.def;
	i.type = "object", i.properties = {};
	let o = a.shape;
	for (let e in o) i.properties[e] = T(o[e], t, {
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
	c.size > 0 && (i.required = Array.from(c)), a.catchall?._zod.def.type === "never" ? i.additionalProperties = !1 : a.catchall ? a.catchall && (i.additionalProperties = T(a.catchall, t, {
		...r,
		path: [...r.path, "additionalProperties"]
	})) : t.io === "output" && (i.additionalProperties = !1);
}, Li = (e, t, n, r) => {
	let i = e._zod.def, a = i.inclusive === !1, o = i.options.map((e, n) => T(e, t, {
		...r,
		path: [
			...r.path,
			a ? "oneOf" : "anyOf",
			n
		]
	}));
	a ? n.oneOf = o : n.anyOf = o;
}, Ri = (e, t, n, r) => {
	let i = e._zod.def, a = T(i.left, t, {
		...r,
		path: [
			...r.path,
			"allOf",
			0
		]
	}), o = T(i.right, t, {
		...r,
		path: [
			...r.path,
			"allOf",
			1
		]
	}), s = (e) => "allOf" in e && Object.keys(e).length === 1;
	n.allOf = [...s(a) ? a.allOf : [a], ...s(o) ? o.allOf : [o]];
}, zi = (e, t, n, r) => {
	let i = n, a = e._zod.def;
	i.type = "object";
	let o = a.keyType, s = o._zod.bag?.patterns;
	if (a.mode === "loose" && s && s.size > 0) {
		let e = T(a.valueType, t, {
			...r,
			path: [
				...r.path,
				"patternProperties",
				"*"
			]
		});
		i.patternProperties = {};
		for (let t of s) i.patternProperties[t.source] = e;
	} else (t.target === "draft-07" || t.target === "draft-2020-12") && (i.propertyNames = T(a.keyType, t, {
		...r,
		path: [...r.path, "propertyNames"]
	})), i.additionalProperties = T(a.valueType, t, {
		...r,
		path: [...r.path, "additionalProperties"]
	});
	let c = o._zod.values;
	if (c) {
		let e = [...c].filter((e) => typeof e == "string" || typeof e == "number");
		e.length > 0 && (i.required = e);
	}
}, Bi = (e, t, n, r) => {
	let i = e._zod.def, a = T(i.innerType, t, r), o = t.seen.get(e);
	t.target === "openapi-3.0" ? (o.ref = i.innerType, n.nullable = !0) : n.anyOf = [a, { type: "null" }];
}, Vi = (e, t, n, r) => {
	let i = e._zod.def;
	T(i.innerType, t, r);
	let a = t.seen.get(e);
	a.ref = i.innerType;
}, Hi = (e, t, n, r) => {
	let i = e._zod.def;
	T(i.innerType, t, r);
	let a = t.seen.get(e);
	a.ref = i.innerType, n.default = JSON.parse(JSON.stringify(i.defaultValue));
}, Ui = (e, t, n, r) => {
	let i = e._zod.def;
	T(i.innerType, t, r);
	let a = t.seen.get(e);
	a.ref = i.innerType, t.io === "input" && (n._prefault = JSON.parse(JSON.stringify(i.defaultValue)));
}, Wi = (e, t, n, r) => {
	let i = e._zod.def;
	T(i.innerType, t, r);
	let a = t.seen.get(e);
	a.ref = i.innerType;
	let o;
	try {
		o = i.catchValue(void 0);
	} catch {
		throw Error("Dynamic catch values are not supported in JSON Schema");
	}
	n.default = o;
}, Gi = (e, t, n, r) => {
	let i = e._zod.def, a = i.in._zod.traits.has("$ZodTransform"), o = t.io === "input" ? a ? i.out : i.in : i.out;
	T(o, t, r);
	let s = t.seen.get(e);
	s.ref = o;
}, Ki = (e, t, n, r) => {
	let i = e._zod.def;
	T(i.innerType, t, r);
	let a = t.seen.get(e);
	a.ref = i.innerType, n.readOnly = !0;
}, qi = (e, t, n, r) => {
	let i = e._zod.def;
	T(i.innerType, t, r);
	let a = t.seen.get(e);
	a.ref = i.innerType;
}, Ji = /*@__PURE__*/ g("ZodISODateTime", (e, t) => {
	_n.init(e, t), A.init(e, t);
});
function Yi(e) {
	return /* @__PURE__ */ Hr(Ji, e);
}
var Xi = /*@__PURE__*/ g("ZodISODate", (e, t) => {
	vn.init(e, t), A.init(e, t);
});
function Zi(e) {
	return /* @__PURE__ */ Ur(Xi, e);
}
var Qi = /*@__PURE__*/ g("ZodISOTime", (e, t) => {
	yn.init(e, t), A.init(e, t);
});
function $i(e) {
	return /* @__PURE__ */ Wr(Qi, e);
}
var ea = /*@__PURE__*/ g("ZodISODuration", (e, t) => {
	bn.init(e, t), A.init(e, t);
});
function ta(e) {
	return /* @__PURE__ */ Gr(ea, e);
}
var D = /*@__PURE__*/ g("ZodError", (e, t) => {
	Ge.init(e, t), e.name = "ZodError", Object.defineProperties(e, {
		format: { value: (t) => Je(e, t) },
		flatten: { value: (t) => qe(e, t) },
		addIssue: { value: (t) => {
			e.issues.push(t), e.message = JSON.stringify(e.issues, fe, 2);
		} },
		addIssues: { value: (t) => {
			e.issues.push(...t), e.message = JSON.stringify(e.issues, fe, 2);
		} },
		isEmpty: { get() {
			return e.issues.length === 0;
		} }
	});
}, { Parent: Error }), na = /* @__PURE__ */ Ye(D), ra = /* @__PURE__ */ Xe(D), ia = /* @__PURE__ */ Ze(D), aa = /* @__PURE__ */ $e(D), oa = /* @__PURE__ */ tt(D), sa = /* @__PURE__ */ nt(D), ca = /* @__PURE__ */ rt(D), la = /* @__PURE__ */ it(D), ua = /* @__PURE__ */ at(D), da = /* @__PURE__ */ ot(D), fa = /* @__PURE__ */ st(D), pa = /* @__PURE__ */ ct(D), ma = /* @__PURE__ */ new WeakMap();
function ha(e, t, n) {
	let r = Object.getPrototypeOf(e), i = ma.get(r);
	if (i || (i = /* @__PURE__ */ new Set(), ma.set(r, i)), !i.has(t)) {
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
var O = /*@__PURE__*/ g("ZodType", (e, t) => (C.init(e, t), Object.assign(e["~standard"], { jsonSchema: {
	input: Ti(e, "input"),
	output: Ti(e, "output")
} }), e.toJSONSchema = wi(e, {}), e.def = t, e.type = t.type, Object.defineProperty(e, "_def", { value: t }), e.parse = (t, n) => na(e, t, n, { callee: e.parse }), e.safeParse = (t, n) => ia(e, t, n), e.parseAsync = async (t, n) => ra(e, t, n, { callee: e.parseAsync }), e.safeParseAsync = async (t, n) => aa(e, t, n), e.spa = e.safeParseAsync, e.encode = (t, n) => oa(e, t, n), e.decode = (t, n) => sa(e, t, n), e.encodeAsync = async (t, n) => ca(e, t, n), e.decodeAsync = async (t, n) => la(e, t, n), e.safeEncode = (t, n) => ua(e, t, n), e.safeDecode = (t, n) => da(e, t, n), e.safeEncodeAsync = async (t, n) => fa(e, t, n), e.safeDecodeAsync = async (t, n) => pa(e, t, n), ha(e, "ZodType", {
	check(...e) {
		let t = this.def;
		return this.clone(ye(t, { checks: [...t.checks ?? [], ...e.map((e) => typeof e == "function" ? { _zod: {
			check: e,
			def: { check: "custom" },
			onattach: []
		} } : e)] }), { parent: !0 });
	},
	with(...e) {
		return this.check(...e);
	},
	clone(e, t) {
		return y(this, e, t);
	},
	brand() {
		return this;
	},
	register(e, t) {
		return e.add(this, t), this;
	},
	refine(e, t) {
		return this.check(bo(e, t));
	},
	superRefine(e, t) {
		return this.check(xo(e, t));
	},
	overwrite(e) {
		return this.check(/* @__PURE__ */ di(e));
	},
	optional() {
		return to(this);
	},
	exactOptional() {
		return ro(this);
	},
	nullable() {
		return ao(this);
	},
	nullish() {
		return to(ao(this));
	},
	nonoptional(e) {
		return fo(this, e);
	},
	array() {
		return F(this);
	},
	or(e) {
		return L([this, e]);
	},
	and(e) {
		return R(this, e);
	},
	transform(e) {
		return go(this, $a(e));
	},
	default(e) {
		return so(this, e);
	},
	prefault(e) {
		return lo(this, e);
	},
	catch(e) {
		return mo(this, e);
	},
	pipe(e) {
		return go(this, e);
	},
	readonly() {
		return vo(this);
	},
	describe(e) {
		let t = this.clone();
		return vr.add(t, { description: e }), t;
	},
	meta(...e) {
		if (e.length === 0) return vr.get(this);
		let t = this.clone();
		return vr.add(t, e[0]), t;
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
		return vr.get(e)?.description;
	},
	configurable: !0
}), e)), ga = /*@__PURE__*/ g("_ZodString", (e, t) => {
	an.init(e, t), O.init(e, t), e._zod.processJSONSchema = (t, n, r) => Di(e, t, n, r);
	let n = e._zod.bag;
	e.format = n.format ?? null, e.minLength = n.minimum ?? null, e.maxLength = n.maximum ?? null, ha(e, "_ZodString", {
		regex(...e) {
			return this.check(/* @__PURE__ */ ai(...e));
		},
		includes(...e) {
			return this.check(/* @__PURE__ */ ci(...e));
		},
		startsWith(...e) {
			return this.check(/* @__PURE__ */ li(...e));
		},
		endsWith(...e) {
			return this.check(/* @__PURE__ */ ui(...e));
		},
		min(...e) {
			return this.check(/* @__PURE__ */ ri(...e));
		},
		max(...e) {
			return this.check(/* @__PURE__ */ ni(...e));
		},
		length(...e) {
			return this.check(/* @__PURE__ */ ii(...e));
		},
		nonempty(...e) {
			return this.check(/* @__PURE__ */ ri(1, ...e));
		},
		lowercase(e) {
			return this.check(/* @__PURE__ */ oi(e));
		},
		uppercase(e) {
			return this.check(/* @__PURE__ */ si(e));
		},
		trim() {
			return this.check(/* @__PURE__ */ pi());
		},
		normalize(...e) {
			return this.check(/* @__PURE__ */ fi(...e));
		},
		toLowerCase() {
			return this.check(/* @__PURE__ */ mi());
		},
		toUpperCase() {
			return this.check(/* @__PURE__ */ hi());
		},
		slugify() {
			return this.check(/* @__PURE__ */ gi());
		}
	});
}), _a = /*@__PURE__*/ g("ZodString", (e, t) => {
	an.init(e, t), ga.init(e, t), e.email = (t) => e.check(/* @__PURE__ */ br(va, t)), e.url = (t) => e.check(/* @__PURE__ */ Er(xa, t)), e.jwt = (t) => e.check(/* @__PURE__ */ Vr(La, t)), e.emoji = (t) => e.check(/* @__PURE__ */ Dr(Ca, t)), e.guid = (t) => e.check(/* @__PURE__ */ xr(ya, t)), e.uuid = (t) => e.check(/* @__PURE__ */ Sr(ba, t)), e.uuidv4 = (t) => e.check(/* @__PURE__ */ Cr(ba, t)), e.uuidv6 = (t) => e.check(/* @__PURE__ */ wr(ba, t)), e.uuidv7 = (t) => e.check(/* @__PURE__ */ Tr(ba, t)), e.nanoid = (t) => e.check(/* @__PURE__ */ Or(wa, t)), e.guid = (t) => e.check(/* @__PURE__ */ xr(ya, t)), e.cuid = (t) => e.check(/* @__PURE__ */ kr(Ta, t)), e.cuid2 = (t) => e.check(/* @__PURE__ */ Ar(Ea, t)), e.ulid = (t) => e.check(/* @__PURE__ */ jr(Da, t)), e.base64 = (t) => e.check(/* @__PURE__ */ Rr(Pa, t)), e.base64url = (t) => e.check(/* @__PURE__ */ zr(Fa, t)), e.xid = (t) => e.check(/* @__PURE__ */ Mr(Oa, t)), e.ksuid = (t) => e.check(/* @__PURE__ */ Nr(ka, t)), e.ipv4 = (t) => e.check(/* @__PURE__ */ Pr(Aa, t)), e.ipv6 = (t) => e.check(/* @__PURE__ */ Fr(ja, t)), e.cidrv4 = (t) => e.check(/* @__PURE__ */ Ir(Ma, t)), e.cidrv6 = (t) => e.check(/* @__PURE__ */ Lr(Na, t)), e.e164 = (t) => e.check(/* @__PURE__ */ Br(Ia, t)), e.datetime = (t) => e.check(Yi(t)), e.date = (t) => e.check(Zi(t)), e.time = (t) => e.check($i(t)), e.duration = (t) => e.check(ta(t));
});
function k(e) {
	return /* @__PURE__ */ yr(_a, e);
}
var A = /*@__PURE__*/ g("ZodStringFormat", (e, t) => {
	w.init(e, t), ga.init(e, t);
}), va = /*@__PURE__*/ g("ZodEmail", (e, t) => {
	cn.init(e, t), A.init(e, t);
}), ya = /*@__PURE__*/ g("ZodGUID", (e, t) => {
	on.init(e, t), A.init(e, t);
}), ba = /*@__PURE__*/ g("ZodUUID", (e, t) => {
	sn.init(e, t), A.init(e, t);
}), xa = /*@__PURE__*/ g("ZodURL", (e, t) => {
	ln.init(e, t), A.init(e, t);
});
function Sa(e) {
	return /* @__PURE__ */ Er(xa, e);
}
var Ca = /*@__PURE__*/ g("ZodEmoji", (e, t) => {
	un.init(e, t), A.init(e, t);
}), wa = /*@__PURE__*/ g("ZodNanoID", (e, t) => {
	dn.init(e, t), A.init(e, t);
}), Ta = /*@__PURE__*/ g("ZodCUID", (e, t) => {
	fn.init(e, t), A.init(e, t);
}), Ea = /*@__PURE__*/ g("ZodCUID2", (e, t) => {
	pn.init(e, t), A.init(e, t);
}), Da = /*@__PURE__*/ g("ZodULID", (e, t) => {
	mn.init(e, t), A.init(e, t);
}), Oa = /*@__PURE__*/ g("ZodXID", (e, t) => {
	hn.init(e, t), A.init(e, t);
}), ka = /*@__PURE__*/ g("ZodKSUID", (e, t) => {
	gn.init(e, t), A.init(e, t);
}), Aa = /*@__PURE__*/ g("ZodIPv4", (e, t) => {
	xn.init(e, t), A.init(e, t);
}), ja = /*@__PURE__*/ g("ZodIPv6", (e, t) => {
	Sn.init(e, t), A.init(e, t);
}), Ma = /*@__PURE__*/ g("ZodCIDRv4", (e, t) => {
	Cn.init(e, t), A.init(e, t);
}), Na = /*@__PURE__*/ g("ZodCIDRv6", (e, t) => {
	wn.init(e, t), A.init(e, t);
}), Pa = /*@__PURE__*/ g("ZodBase64", (e, t) => {
	En.init(e, t), A.init(e, t);
}), Fa = /*@__PURE__*/ g("ZodBase64URL", (e, t) => {
	On.init(e, t), A.init(e, t);
}), Ia = /*@__PURE__*/ g("ZodE164", (e, t) => {
	kn.init(e, t), A.init(e, t);
}), La = /*@__PURE__*/ g("ZodJWT", (e, t) => {
	jn.init(e, t), A.init(e, t);
}), Ra = /*@__PURE__*/ g("ZodNumber", (e, t) => {
	Mn.init(e, t), O.init(e, t), e._zod.processJSONSchema = (t, n, r) => Oi(e, t, n, r), ha(e, "ZodNumber", {
		gt(e, t) {
			return this.check(/* @__PURE__ */ $r(e, t));
		},
		gte(e, t) {
			return this.check(/* @__PURE__ */ ei(e, t));
		},
		min(e, t) {
			return this.check(/* @__PURE__ */ ei(e, t));
		},
		lt(e, t) {
			return this.check(/* @__PURE__ */ Zr(e, t));
		},
		lte(e, t) {
			return this.check(/* @__PURE__ */ Qr(e, t));
		},
		max(e, t) {
			return this.check(/* @__PURE__ */ Qr(e, t));
		},
		int(e) {
			return this.check(M(e));
		},
		safe(e) {
			return this.check(M(e));
		},
		positive(e) {
			return this.check(/* @__PURE__ */ $r(0, e));
		},
		nonnegative(e) {
			return this.check(/* @__PURE__ */ ei(0, e));
		},
		negative(e) {
			return this.check(/* @__PURE__ */ Zr(0, e));
		},
		nonpositive(e) {
			return this.check(/* @__PURE__ */ Qr(0, e));
		},
		multipleOf(e, t) {
			return this.check(/* @__PURE__ */ ti(e, t));
		},
		step(e, t) {
			return this.check(/* @__PURE__ */ ti(e, t));
		},
		finite() {
			return this;
		}
	});
	let n = e._zod.bag;
	e.minValue = Math.max(n.minimum ?? -Infinity, n.exclusiveMinimum ?? -Infinity) ?? null, e.maxValue = Math.min(n.maximum ?? Infinity, n.exclusiveMaximum ?? Infinity) ?? null, e.isInt = (n.format ?? "").includes("int") || Number.isSafeInteger(n.multipleOf ?? .5), e.isFinite = !0, e.format = n.format ?? null;
});
function j(e) {
	return /* @__PURE__ */ Kr(Ra, e);
}
var za = /*@__PURE__*/ g("ZodNumberFormat", (e, t) => {
	Nn.init(e, t), Ra.init(e, t);
});
function M(e) {
	return /* @__PURE__ */ qr(za, e);
}
var Ba = /*@__PURE__*/ g("ZodBoolean", (e, t) => {
	Pn.init(e, t), O.init(e, t), e._zod.processJSONSchema = (t, n, r) => ki(e, t, n, r);
});
function N(e) {
	return /* @__PURE__ */ Jr(Ba, e);
}
var Va = /*@__PURE__*/ g("ZodUnknown", (e, t) => {
	Fn.init(e, t), O.init(e, t), e._zod.processJSONSchema = (e, t, n) => void 0;
});
function P() {
	return /* @__PURE__ */ Yr(Va);
}
var Ha = /*@__PURE__*/ g("ZodNever", (e, t) => {
	In.init(e, t), O.init(e, t), e._zod.processJSONSchema = (t, n, r) => Ai(e, t, n, r);
});
function Ua(e) {
	return /* @__PURE__ */ Xr(Ha, e);
}
var Wa = /*@__PURE__*/ g("ZodArray", (e, t) => {
	Rn.init(e, t), O.init(e, t), e._zod.processJSONSchema = (t, n, r) => Fi(e, t, n, r), e.element = t.element, ha(e, "ZodArray", {
		min(e, t) {
			return this.check(/* @__PURE__ */ ri(e, t));
		},
		nonempty(e) {
			return this.check(/* @__PURE__ */ ri(1, e));
		},
		max(e, t) {
			return this.check(/* @__PURE__ */ ni(e, t));
		},
		length(e, t) {
			return this.check(/* @__PURE__ */ ii(e, t));
		},
		unwrap() {
			return this.element;
		}
	});
});
function F(e, t) {
	return /* @__PURE__ */ _i(Wa, e, t);
}
var Ga = /*@__PURE__*/ g("ZodObject", (e, t) => {
	Un.init(e, t), O.init(e, t), e._zod.processJSONSchema = (t, n, r) => Ii(e, t, n, r), v(e, "shape", () => t.shape), ha(e, "ZodObject", {
		keyof() {
			return Xa(Object.keys(this._zod.def.shape));
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
				catchall: P()
			});
		},
		loose() {
			return this.clone({
				...this._zod.def,
				catchall: P()
			});
		},
		strict() {
			return this.clone({
				...this._zod.def,
				catchall: Ua()
			});
		},
		strip() {
			return this.clone({
				...this._zod.def,
				catchall: void 0
			});
		},
		extend(e) {
			return Ne(this, e);
		},
		safeExtend(e) {
			return Pe(this, e);
		},
		merge(e) {
			return Fe(this, e);
		},
		pick(e) {
			return je(this, e);
		},
		omit(e) {
			return Me(this, e);
		},
		partial(...e) {
			return Ie(eo, this, e[0]);
		},
		required(...e) {
			return Le(uo, this, e[0]);
		}
	});
});
function I(e, t) {
	return new Ga({
		type: "object",
		shape: e ?? {},
		...b(t)
	});
}
var Ka = /*@__PURE__*/ g("ZodUnion", (e, t) => {
	Gn.init(e, t), O.init(e, t), e._zod.processJSONSchema = (t, n, r) => Li(e, t, n, r), e.options = t.options;
});
function L(e, t) {
	return new Ka({
		type: "union",
		options: e,
		...b(t)
	});
}
var qa = /*@__PURE__*/ g("ZodIntersection", (e, t) => {
	Kn.init(e, t), O.init(e, t), e._zod.processJSONSchema = (t, n, r) => Ri(e, t, n, r);
});
function R(e, t) {
	return new qa({
		type: "intersection",
		left: e,
		right: t
	});
}
var Ja = /*@__PURE__*/ g("ZodRecord", (e, t) => {
	Yn.init(e, t), O.init(e, t), e._zod.processJSONSchema = (t, n, r) => zi(e, t, n, r), e.keyType = t.keyType, e.valueType = t.valueType;
});
function z(e, t, n) {
	return !t || !t._zod ? new Ja({
		type: "record",
		keyType: k(),
		valueType: e,
		...b(t)
	}) : new Ja({
		type: "record",
		keyType: e,
		valueType: t,
		...b(n)
	});
}
var Ya = /*@__PURE__*/ g("ZodEnum", (e, t) => {
	Xn.init(e, t), O.init(e, t), e._zod.processJSONSchema = (t, n, r) => ji(e, t, n, r), e.enum = t.entries, e.options = Object.values(t.entries);
	let n = new Set(Object.keys(t.entries));
	e.extract = (e, r) => {
		let i = {};
		for (let r of e) if (n.has(r)) i[r] = t.entries[r];
		else throw Error(`Key ${r} not found in enum`);
		return new Ya({
			...t,
			checks: [],
			...b(r),
			entries: i
		});
	}, e.exclude = (e, r) => {
		let i = { ...t.entries };
		for (let t of e) if (n.has(t)) delete i[t];
		else throw Error(`Key ${t} not found in enum`);
		return new Ya({
			...t,
			checks: [],
			...b(r),
			entries: i
		});
	};
});
function Xa(e, t) {
	return new Ya({
		type: "enum",
		entries: Array.isArray(e) ? Object.fromEntries(e.map((e) => [e, e])) : e,
		...b(t)
	});
}
var Za = /*@__PURE__*/ g("ZodLiteral", (e, t) => {
	Zn.init(e, t), O.init(e, t), e._zod.processJSONSchema = (t, n, r) => Mi(e, t, n, r), e.values = new Set(t.values), Object.defineProperty(e, "value", { get() {
		if (t.values.length > 1) throw Error("This schema contains multiple valid literal values. Use `.values` instead.");
		return t.values[0];
	} });
});
function B(e, t) {
	return new Za({
		type: "literal",
		values: Array.isArray(e) ? e : [e],
		...b(t)
	});
}
var Qa = /*@__PURE__*/ g("ZodTransform", (e, t) => {
	Qn.init(e, t), O.init(e, t), e._zod.processJSONSchema = (t, n, r) => Pi(e, t, n, r), e._zod.parse = (n, r) => {
		if (r.direction === "backward") throw new le(e.constructor.name);
		n.addIssue = (r) => {
			if (typeof r == "string") n.issues.push(Ue(r, n.value, t));
			else {
				let t = r;
				t.fatal && (t.continue = !1), t.code ??= "custom", t.input ??= n.value, t.inst ??= e, n.issues.push(Ue(t));
			}
		};
		let i = t.transform(n.value, n);
		return i instanceof Promise ? i.then((e) => (n.value = e, n.fallback = !0, n)) : (n.value = i, n.fallback = !0, n);
	};
});
function $a(e) {
	return new Qa({
		type: "transform",
		transform: e
	});
}
var eo = /*@__PURE__*/ g("ZodOptional", (e, t) => {
	er.init(e, t), O.init(e, t), e._zod.processJSONSchema = (t, n, r) => qi(e, t, n, r), e.unwrap = () => e._zod.def.innerType;
});
function to(e) {
	return new eo({
		type: "optional",
		innerType: e
	});
}
var no = /*@__PURE__*/ g("ZodExactOptional", (e, t) => {
	tr.init(e, t), O.init(e, t), e._zod.processJSONSchema = (t, n, r) => qi(e, t, n, r), e.unwrap = () => e._zod.def.innerType;
});
function ro(e) {
	return new no({
		type: "optional",
		innerType: e
	});
}
var io = /*@__PURE__*/ g("ZodNullable", (e, t) => {
	nr.init(e, t), O.init(e, t), e._zod.processJSONSchema = (t, n, r) => Bi(e, t, n, r), e.unwrap = () => e._zod.def.innerType;
});
function ao(e) {
	return new io({
		type: "nullable",
		innerType: e
	});
}
var oo = /*@__PURE__*/ g("ZodDefault", (e, t) => {
	rr.init(e, t), O.init(e, t), e._zod.processJSONSchema = (t, n, r) => Hi(e, t, n, r), e.unwrap = () => e._zod.def.innerType, e.removeDefault = e.unwrap;
});
function so(e, t) {
	return new oo({
		type: "default",
		innerType: e,
		get defaultValue() {
			return typeof t == "function" ? t() : Ee(t);
		}
	});
}
var co = /*@__PURE__*/ g("ZodPrefault", (e, t) => {
	ar.init(e, t), O.init(e, t), e._zod.processJSONSchema = (t, n, r) => Ui(e, t, n, r), e.unwrap = () => e._zod.def.innerType;
});
function lo(e, t) {
	return new co({
		type: "prefault",
		innerType: e,
		get defaultValue() {
			return typeof t == "function" ? t() : Ee(t);
		}
	});
}
var uo = /*@__PURE__*/ g("ZodNonOptional", (e, t) => {
	or.init(e, t), O.init(e, t), e._zod.processJSONSchema = (t, n, r) => Vi(e, t, n, r), e.unwrap = () => e._zod.def.innerType;
});
function fo(e, t) {
	return new uo({
		type: "nonoptional",
		innerType: e,
		...b(t)
	});
}
var po = /*@__PURE__*/ g("ZodCatch", (e, t) => {
	cr.init(e, t), O.init(e, t), e._zod.processJSONSchema = (t, n, r) => Wi(e, t, n, r), e.unwrap = () => e._zod.def.innerType, e.removeCatch = e.unwrap;
});
function mo(e, t) {
	return new po({
		type: "catch",
		innerType: e,
		catchValue: typeof t == "function" ? t : () => t
	});
}
var ho = /*@__PURE__*/ g("ZodPipe", (e, t) => {
	lr.init(e, t), O.init(e, t), e._zod.processJSONSchema = (t, n, r) => Gi(e, t, n, r), e.in = t.in, e.out = t.out;
});
function go(e, t) {
	return new ho({
		type: "pipe",
		in: e,
		out: t
	});
}
var _o = /*@__PURE__*/ g("ZodReadonly", (e, t) => {
	dr.init(e, t), O.init(e, t), e._zod.processJSONSchema = (t, n, r) => Ki(e, t, n, r), e.unwrap = () => e._zod.def.innerType;
});
function vo(e) {
	return new _o({
		type: "readonly",
		innerType: e
	});
}
var yo = /*@__PURE__*/ g("ZodCustom", (e, t) => {
	pr.init(e, t), O.init(e, t), e._zod.processJSONSchema = (t, n, r) => Ni(e, t, n, r);
});
function bo(e, t = {}) {
	return /* @__PURE__ */ vi(yo, e, t);
}
function xo(e, t) {
	return /* @__PURE__ */ yi(e, t);
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/schema-deserialize.js
var So = Symbol("skippedItem");
function V(e, t) {
	return e.catch(t);
}
function H(e, t) {
	let n = e.catch(t);
	return P().transform((e, t) => e === void 0 ? (t.addIssue({
		code: "custom",
		message: "Required value is missing"
	}), se) : n.parse(e));
}
function Co(e, t) {
	if (typeof e != "object" || !e || Array.isArray(e)) return;
	let n = e[t];
	return typeof n == "string" ? n : void 0;
}
function wo(e, t, n) {
	return e.superRefine((e, r) => {
		let i = Co(e, t);
		i !== void 0 && n.includes(i) && r.addIssue({
			code: "custom",
			path: [t],
			message: `${t} ${JSON.stringify(i)} is reserved by a known variant, but the value does not match that variant's schema`
		});
	});
}
function To(e, t, n) {
	return P().transform((r, i) => {
		let a = e.safeParse(r);
		if (!a.success) {
			for (let e of a.error.issues) i.addIssue({
				...e,
				input: r
			});
			return se;
		}
		let o = a.data, s = Co(r, t);
		if (s !== void 0 && !n.includes(s)) {
			let e = r;
			for (let [t, n] of Object.entries(e)) t !== "__proto__" && (Object.hasOwn(o, t) || (o[t] = n));
		}
		return o;
	});
}
function U(e) {
	return F(e.catch(So)).transform((e) => e.filter((e) => e !== So));
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/schema/zod.gen.js
var Eo = L([j(), k()]).nullable(), W = k(), Do = I({
	sessionId: W,
	path: k(),
	content: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Oo = I({
	sessionId: W,
	path: k(),
	line: V(M().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	limit: V(M().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), ko = k(), Ao = L([
	B("read"),
	B("edit"),
	B("delete"),
	B("move"),
	B("search"),
	B("execute"),
	B("think"),
	B("fetch"),
	B("switch_mode"),
	B("other")
]), jo = L([
	B("pending"),
	B("in_progress"),
	B("completed"),
	B("failed")
]), Mo = I({
	audience: V(U(L([B("assistant"), B("user")])).nullish(), () => void 0),
	lastModified: V(k().nullish(), () => void 0),
	priority: V(j().nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), No = I({
	annotations: V(Mo.nullish(), () => void 0),
	text: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Po = I({
	annotations: V(Mo.nullish(), () => void 0),
	data: k(),
	mimeType: k(),
	uri: V(k().nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Fo = I({
	annotations: V(Mo.nullish(), () => void 0),
	data: k(),
	mimeType: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Io = I({
	annotations: V(Mo.nullish(), () => void 0),
	description: V(k().nullish(), () => void 0),
	mimeType: V(k().nullish(), () => void 0),
	name: k(),
	size: V(j().nullish(), () => void 0),
	title: V(k().nullish(), () => void 0),
	uri: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Lo = L([I({
	mimeType: V(k().nullish(), () => void 0),
	text: k(),
	uri: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), I({
	blob: k(),
	mimeType: V(k().nullish(), () => void 0),
	uri: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
})]), Ro = I({
	annotations: V(Mo.nullish(), () => void 0),
	resource: Lo,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), zo = L([
	No.and(I({ type: B("text") })),
	Po.and(I({ type: B("image") })),
	Fo.and(I({ type: B("audio") })),
	Io.and(I({ type: B("resource_link") })),
	Ro.and(I({ type: B("resource") }))
]), Bo = I({
	content: zo,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Vo = I({
	path: k(),
	oldText: V(k().nullish(), () => void 0),
	newText: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Ho = k(), Uo = I({
	terminalId: Ho,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Wo = L([
	Bo.and(I({ type: B("content") })),
	Vo.and(I({ type: B("diff") })),
	Uo.and(I({ type: B("terminal") }))
]), Go = I({
	path: k(),
	line: V(M().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Ko = I({
	toolCallId: ko,
	kind: V(Ao.nullish(), () => void 0),
	status: V(jo.nullish(), () => void 0),
	title: V(k().nullish(), () => void 0),
	name: V(k().nullish(), () => void 0),
	content: V(U(Wo).nullish(), () => void 0),
	locations: V(U(Go).nullish(), () => void 0),
	rawInput: V(P().optional(), () => void 0),
	rawOutput: V(P().optional(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), qo = k(), Jo = L([
	B("allow_once"),
	B("allow_always"),
	B("reject_once"),
	B("reject_always")
]), Yo = I({
	sessionId: W,
	toolCall: Ko,
	options: F(I({
		optionId: qo,
		name: k(),
		kind: Jo,
		_meta: V(z(k(), P()).nullish(), () => void 0)
	})),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Xo = I({
	name: k(),
	value: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Zo = I({
	sessionId: W,
	command: k(),
	args: V(U(k()).optional(), () => []),
	env: V(U(Xo).optional(), () => []),
	cwd: V(k().nullish(), () => void 0),
	outputByteLimit: V(j().nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Qo = I({
	sessionId: W,
	terminalId: Ho,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), $o = I({
	sessionId: W,
	terminalId: Ho,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), es = I({
	sessionId: W,
	terminalId: Ho,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), ts = I({
	sessionId: W,
	terminalId: Ho,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), ns = I({
	sessionId: W,
	toolCallId: V(ko.nullish(), () => void 0)
}), rs = I({ requestId: Eo }), is = B("object"), as = L([
	B("email"),
	B("uri"),
	B("date"),
	B("date-time")
]), os = I({
	const: k(),
	title: k(),
	description: V(k().nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), ss = I({
	title: V(k().nullish(), () => void 0),
	description: V(k().nullish(), () => void 0),
	minLength: M().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(),
	maxLength: M().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(),
	pattern: k().nullish(),
	format: as.nullish(),
	default: V(k().nullish(), () => void 0),
	enum: F(k()).nullish(),
	oneOf: F(os).nullish(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), cs = I({
	title: V(k().nullish(), () => void 0),
	description: V(k().nullish(), () => void 0),
	minimum: j().nullish(),
	maximum: j().nullish(),
	default: V(j().nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), ls = I({
	title: V(k().nullish(), () => void 0),
	description: V(k().nullish(), () => void 0),
	minimum: j().nullish(),
	maximum: j().nullish(),
	default: V(j().nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), us = I({
	title: V(k().nullish(), () => void 0),
	description: V(k().nullish(), () => void 0),
	default: V(N().nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), ds = I({
	enum: F(k()),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), fs = I({
	anyOf: F(os),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), ps = To(L([
	ds.and(I({ type: B("string") })),
	wo(I({ type: k() }), "type", ["string"]),
	fs
]), "type", ["string"]), ms = I({
	title: V(k().nullish(), () => void 0),
	description: V(k().nullish(), () => void 0),
	minItems: j().nullish(),
	maxItems: j().nullish(),
	items: ps,
	default: V(U(k()).nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), hs = To(L([
	ss.and(I({ type: B("string") })),
	cs.and(I({ type: B("number") })),
	ls.and(I({ type: B("integer") })),
	us.and(I({ type: B("boolean") })),
	ms.and(I({ type: B("array") })),
	wo(I({ type: k() }), "type", [
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
]), gs = I({
	type: V(is.optional().default("object"), () => "object"),
	title: V(k().nullish(), () => void 0),
	properties: z(k(), hs).optional().default({}),
	required: F(k()).nullish(),
	description: V(k().nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), _s = R(L([ns, rs]), I({ requestedSchema: gs })), vs = k(), ys = R(L([ns, rs]), I({
	elicitationId: vs,
	url: Sa()
})), bs = To(R(L([
	_s.and(I({ mode: B("form") })),
	ys.and(I({ mode: B("url") })),
	wo(R(L([ns, rs]), I({ mode: k() })), "mode", ["form", "url"])
]), I({
	message: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
})), "mode", ["form", "url"]), xs = k(), Ss = I({
	serverId: xs,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Cs = k(), ws = I({
	connectionId: Cs,
	method: k(),
	params: z(k(), P()).nullish(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Ts = I({
	connectionId: Cs,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Es = P();
I({
	id: Eo,
	method: k(),
	params: L([
		Do,
		Oo,
		Yo,
		Zo,
		Qo,
		$o,
		es,
		ts,
		bs,
		Ss,
		ws,
		Ts,
		Es
	]).nullish()
});
var Ds = M().gte(0).lte(65535), Os = I({
	image: V(N().optional().default(!1), () => !1),
	audio: V(N().optional().default(!1), () => !1),
	embeddedContext: V(N().optional().default(!1), () => !1),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), ks = I({
	http: V(N().optional().default(!1), () => !1),
	sse: V(N().optional().default(!1), () => !1),
	acp: V(N().optional().default(!1), () => !1),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), As = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), js = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), Ms = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), Ns = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), Ps = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), Fs = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), Is = I({
	list: V(As.nullish(), () => void 0),
	delete: V(js.nullish(), () => void 0),
	additionalDirectories: V(Ms.nullish(), () => void 0),
	fork: V(Ns.nullish(), () => void 0),
	resume: V(Ps.nullish(), () => void 0),
	close: V(Fs.nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Ls = I({
	logout: V(I({ _meta: V(z(k(), P()).nullish(), () => void 0) }).nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Rs = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), zs = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), Bs = I({
	syncKind: L([B("full"), B("incremental")]),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Vs = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), Hs = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), Us = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), Ws = I({
	document: V(I({
		didOpen: V(zs.nullish(), () => void 0),
		didChange: V(Bs.nullish(), () => void 0),
		didClose: V(Vs.nullish(), () => void 0),
		didSave: V(Hs.nullish(), () => void 0),
		didFocus: V(Us.nullish(), () => void 0),
		_meta: V(z(k(), P()).nullish(), () => void 0)
	}).nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Gs = I({
	maxCount: V(M().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Ks = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), qs = I({
	maxCount: V(M().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Js = I({
	maxCount: V(M().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Ys = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), Xs = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), Zs = I({
	recentFiles: V(Gs.nullish(), () => void 0),
	relatedSnippets: V(Ks.nullish(), () => void 0),
	editHistory: V(qs.nullish(), () => void 0),
	userActions: V(Js.nullish(), () => void 0),
	openFiles: V(Ys.nullish(), () => void 0),
	diagnostics: V(Xs.nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Qs = I({
	events: V(Ws.nullish(), () => void 0),
	context: V(Zs.nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), $s = L([
	B("utf-16"),
	B("utf-32"),
	B("utf-8")
]), ec = I({
	loadSession: V(N().optional().default(!1), () => !1),
	promptCapabilities: V(Os.optional().default({
		image: !1,
		audio: !1,
		embeddedContext: !1
	}), () => ({
		image: !1,
		audio: !1,
		embeddedContext: !1
	})),
	mcpCapabilities: V(ks.optional().default({
		http: !1,
		sse: !1,
		acp: !1
	}), () => ({
		http: !1,
		sse: !1,
		acp: !1
	})),
	sessionCapabilities: V(Is.optional().default({}), () => ({})),
	auth: V(Ls.optional().default({}), () => ({})),
	providers: V(Rs.nullish(), () => void 0),
	nes: V(Qs.nullish(), () => void 0),
	positionEncoding: V($s.nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), tc = k(), nc = I({
	id: tc,
	name: k(),
	description: V(k().nullish(), () => void 0),
	args: V(U(k()).optional(), () => []),
	env: V(z(k(), k()).optional(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), rc = I({
	id: tc,
	name: k(),
	description: V(k().nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), ic = L([nc.and(I({ type: B("terminal") })), rc]), ac = I({
	name: k(),
	title: V(k().nullish(), () => void 0),
	version: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), oc = I({
	protocolVersion: Ds,
	agentCapabilities: V(ec.optional().default({
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
	authMethods: V(U(ic).optional().default([]), () => []),
	agentInfo: V(ac.nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), sc = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), cc = k(), lc = L([
	B("anthropic"),
	B("openai"),
	B("azure"),
	B("vertex"),
	B("bedrock"),
	k()
]), uc = I({
	apiType: lc,
	baseUrl: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), dc = I({
	providers: F(I({
		providerId: cc,
		supported: H(U(lc), () => []),
		required: N(),
		current: uc.nullish(),
		_meta: V(z(k(), P()).nullish(), () => void 0)
	})),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), fc = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), pc = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), mc = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), hc = k(), gc = I({
	currentModeId: hc,
	availableModes: H(U(I({
		id: hc,
		name: k(),
		description: V(k().nullish(), () => void 0),
		_meta: V(z(k(), P()).nullish(), () => void 0)
	})), () => []),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), _c = k(), vc = L([
	B("mode"),
	B("model"),
	B("model_config"),
	B("thought_level"),
	k()
]), yc = k(), bc = I({
	value: yc,
	name: k(),
	description: V(k().nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), xc = I({
	group: k(),
	name: k(),
	options: H(U(bc), () => []),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Sc = I({
	currentValue: yc,
	options: L([F(bc), F(xc)])
}), Cc = I({ currentValue: N() }), wc = R(L([Sc.and(I({ type: B("select") })), Cc.and(I({ type: B("boolean") }))]), I({
	id: _c,
	name: k(),
	description: V(k().nullish(), () => void 0),
	category: V(vc.nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
})), Tc = I({
	sessionId: W,
	modes: V(gc.nullish(), () => void 0),
	configOptions: V(U(wc).nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Ec = I({
	modes: V(gc.nullish(), () => void 0),
	configOptions: V(U(wc).nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Dc = I({
	sessions: H(U(I({
		sessionId: W,
		cwd: k(),
		additionalDirectories: V(U(k()).optional(), () => []),
		title: V(k().nullish(), () => void 0),
		updatedAt: V(k().nullish(), () => void 0),
		_meta: V(z(k(), P()).nullish(), () => void 0)
	})), () => []),
	nextCursor: V(k().nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Oc = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), kc = I({
	sessionId: W,
	modes: V(gc.nullish(), () => void 0),
	configOptions: V(U(wc).nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Ac = I({
	modes: V(gc.nullish(), () => void 0),
	configOptions: V(U(wc).nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), jc = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), Mc = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), Nc = I({
	configOptions: H(U(wc), () => []),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Pc = I({
	stopReason: L([
		B("end_turn"),
		B("max_tokens"),
		B("max_turn_requests"),
		B("refusal"),
		B("cancelled")
	]),
	usage: V(I({
		totalTokens: j(),
		inputTokens: j(),
		outputTokens: j(),
		thoughtTokens: V(j().nullish(), () => void 0),
		cachedReadTokens: V(j().nullish(), () => void 0),
		cachedWriteTokens: V(j().nullish(), () => void 0),
		_meta: V(z(k(), P()).nullish(), () => void 0)
	}).nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Fc = I({
	sessionId: W,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Ic = k(), Lc = I({
	line: M().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }),
	character: M().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Rc = I({
	start: Lc,
	end: Lc,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), zc = I({
	range: Rc,
	newText: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Bc = I({
	id: Ic,
	uri: k(),
	edits: F(zc),
	cursorPosition: V(Lc.nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Vc = I({
	id: Ic,
	uri: k(),
	position: Lc,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Hc = I({
	id: Ic,
	uri: k(),
	position: Lc,
	newName: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Uc = I({
	id: Ic,
	uri: k(),
	search: k(),
	replace: k(),
	isRegex: N().nullish(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Wc = I({
	suggestions: F(L([
		Bc.and(I({ kind: B("edit") })),
		Vc.and(I({ kind: B("jump") })),
		Hc.and(I({ kind: B("rename") })),
		Uc.and(I({ kind: B("searchAndReplace") }))
	])),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Gc = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), Kc = P(), qc = P(), Jc = I({
	code: L([
		B(-32700),
		B(-32600),
		B(-32601),
		B(-32602),
		B(-32603),
		B(-32800),
		B(-32e3),
		B(-32002),
		M().min(-2147483648, { error: "Invalid value: Expected int32 to be >= -2147483648" }).max(2147483647, { error: "Invalid value: Expected int32 to be <= 2147483647" })
	]),
	message: k(),
	data: V(P().optional(), () => void 0)
});
L([I({
	id: Eo,
	result: L([
		oc,
		sc,
		dc,
		fc,
		pc,
		mc,
		Tc,
		Ec,
		Dc,
		Oc,
		kc,
		Ac,
		jc,
		Mc,
		Nc,
		Pc,
		Fc,
		Wc,
		Gc,
		Kc,
		qc
	])
}), I({
	id: Eo,
	error: Jc
})]);
var Yc = I({
	content: zo,
	messageId: V(k().nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Xc = I({
	toolCallId: ko,
	title: k(),
	name: V(k().nullish(), () => void 0),
	kind: V(Ao.optional(), () => void 0),
	status: V(jo.optional(), () => void 0),
	content: V(U(Wo).optional(), () => []),
	locations: V(U(Go).optional(), () => []),
	rawInput: V(P().optional(), () => void 0),
	rawOutput: V(P().optional(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Zc = L([
	B("high"),
	B("medium"),
	B("low")
]), Qc = L([
	B("pending"),
	B("in_progress"),
	B("completed")
]), $c = I({
	content: k(),
	priority: Zc,
	status: Qc,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), el = I({
	entries: H(U($c), () => []),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), tl = k(), nl = I({
	planId: tl,
	entries: H(U($c), () => []),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), rl = I({
	planId: tl,
	uri: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), il = I({
	planId: tl,
	content: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), al = I({
	plan: L([
		nl.and(I({ type: B("items") })),
		rl.and(I({ type: B("file") })),
		il.and(I({ type: B("markdown") }))
	]),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), ol = I({
	planId: tl,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), sl = I({
	hint: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), cl = I({
	availableCommands: H(U(I({
		name: k(),
		description: k(),
		input: V(sl.nullish(), () => void 0),
		_meta: V(z(k(), P()).nullish(), () => void 0)
	})), () => []),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), ll = I({
	currentModeId: hc,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), ul = I({
	configOptions: H(U(wc), () => []),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), dl = I({
	title: V(k().nullish(), () => void 0),
	updatedAt: V(k().nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), fl = I({
	amount: j(),
	currency: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), pl = I({
	used: j(),
	size: j(),
	cost: V(fl.nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), ml = k(), hl = I({
	compactionId: ml,
	status: L([
		B("in_progress"),
		B("completed"),
		B("failed"),
		B("cancelled"),
		k()
	]),
	summary: V(U(zo).nullish(), () => void 0),
	error: V(k().nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), gl = I({
	compactionId: ml,
	content: zo,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), _l = I({
	sessionId: W,
	update: L([
		Yc.and(I({ sessionUpdate: B("user_message_chunk") })),
		Yc.and(I({ sessionUpdate: B("agent_message_chunk") })),
		Yc.and(I({ sessionUpdate: B("agent_thought_chunk") })),
		Xc.and(I({ sessionUpdate: B("tool_call") })),
		Ko.and(I({ sessionUpdate: B("tool_call_update") })),
		el.and(I({ sessionUpdate: B("plan") })),
		al.and(I({ sessionUpdate: B("plan_update") })),
		ol.and(I({ sessionUpdate: B("plan_removed") })),
		cl.and(I({ sessionUpdate: B("available_commands_update") })),
		ll.and(I({ sessionUpdate: B("current_mode_update") })),
		ul.and(I({ sessionUpdate: B("config_option_update") })),
		dl.and(I({ sessionUpdate: B("session_info_update") })),
		pl.and(I({ sessionUpdate: B("usage_update") })),
		hl.and(I({ sessionUpdate: B("compaction_update") })),
		gl.and(I({ sessionUpdate: B("compaction_summary_chunk") }))
	]),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), vl = I({
	elicitationId: vs,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), yl = I({
	connectionId: Cs,
	method: k(),
	params: V(z(k(), P()).nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), bl = P();
I({
	method: k(),
	params: L([
		_l,
		vl,
		yl,
		bl
	]).nullish()
});
var xl = I({
	readTextFile: V(N().optional().default(!1), () => !1),
	writeTextFile: V(N().optional().default(!1), () => !1),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Sl = z(k(), P()), Cl = I({
	boolean: V(I({ _meta: V(z(k(), P()).nullish(), () => void 0) }).nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), wl = I({
	compaction: V(Sl.nullish(), () => void 0),
	configOptions: V(Cl.nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Tl = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), El = I({
	terminal: V(N().optional().default(!1), () => !1),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Dl = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), Ol = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), kl = I({
	form: V(Dl.nullish(), () => void 0),
	url: V(Ol.nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Al = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), jl = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), Ml = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), Nl = I({
	jump: V(Al.nullish(), () => void 0),
	rename: V(jl.nullish(), () => void 0),
	searchAndReplace: V(Ml.nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Pl = I({
	protocolVersion: Ds,
	clientCapabilities: V(I({
		fs: V(xl.optional().default({
			readTextFile: !1,
			writeTextFile: !1
		}), () => ({
			readTextFile: !1,
			writeTextFile: !1
		})),
		terminal: V(N().optional().default(!1), () => !1),
		session: V(wl.nullish(), () => void 0),
		plan: V(Tl.nullish(), () => void 0),
		auth: V(El.optional().default({ terminal: !1 }), () => ({ terminal: !1 })),
		elicitation: V(kl.nullish(), () => void 0),
		nes: V(Nl.nullish(), () => void 0),
		positionEncodings: V(U($s).optional(), () => []),
		_meta: V(z(k(), P()).nullish(), () => void 0)
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
	clientInfo: V(ac.nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Fl = I({
	methodId: tc,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Il = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), Ll = I({
	providerId: cc,
	apiType: lc,
	baseUrl: k(),
	headers: z(k(), k()).optional(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Rl = I({
	providerId: cc,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), zl = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), Bl = I({
	name: k(),
	value: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Vl = I({
	name: k(),
	url: k(),
	headers: F(Bl),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Hl = I({
	name: k(),
	url: k(),
	headers: F(Bl),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Ul = I({
	name: k(),
	serverId: xs,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Wl = I({
	name: k(),
	command: k(),
	args: F(k()),
	env: F(Xo),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Gl = L([
	Vl.and(I({ type: B("http") })),
	Hl.and(I({ type: B("sse") })),
	Ul.and(I({ type: B("acp") })),
	Wl
]), Kl = I({
	cwd: k(),
	additionalDirectories: V(U(k()).optional(), () => []),
	mcpServers: H(U(Gl), () => []),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), ql = I({
	mcpServers: H(U(Gl), () => []),
	cwd: k(),
	additionalDirectories: V(U(k()).optional(), () => []),
	sessionId: W,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Jl = I({
	cwd: k().nullish(),
	cursor: k().nullish(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Yl = I({
	sessionId: W,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Xl = I({
	sessionId: W,
	cwd: k(),
	additionalDirectories: V(U(k()).optional(), () => []),
	mcpServers: V(U(Gl).optional(), () => []),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Zl = I({
	sessionId: W,
	cwd: k(),
	additionalDirectories: V(U(k()).optional(), () => []),
	mcpServers: V(U(Gl).optional(), () => []),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Ql = I({
	sessionId: W,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), $l = I({
	sessionId: W,
	modeId: hc,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), eu = R(L([I({
	value: N(),
	type: B("boolean")
}), I({ value: yc })]), I({
	sessionId: W,
	configId: _c,
	_meta: V(z(k(), P()).nullish(), () => void 0)
})), tu = I({
	sessionId: W,
	prompt: F(zo),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), nu = I({
	uri: k(),
	name: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), ru = I({
	name: k(),
	owner: k(),
	remoteUrl: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), iu = I({
	workspaceUri: V(k().nullish(), () => void 0),
	workspaceFolders: F(nu).nullish(),
	repository: V(ru.nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), au = L([
	B("automatic"),
	B("diagnostic"),
	B("manual")
]), ou = I({
	uri: k(),
	languageId: k(),
	text: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), su = I({
	startLine: M().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }),
	endLine: M().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }),
	text: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), cu = I({
	uri: k(),
	excerpts: F(su),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), lu = I({
	uri: k(),
	diff: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), uu = I({
	action: k(),
	uri: k(),
	position: Lc,
	timestampMs: j(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), du = I({
	uri: k(),
	languageId: k(),
	visibleRange: V(Rc.nullish(), () => void 0),
	lastFocusedMs: V(j().nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), fu = L([
	B("error"),
	B("warning"),
	B("information"),
	B("hint")
]), pu = I({
	uri: k(),
	range: Rc,
	severity: fu,
	message: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), mu = I({
	recentFiles: F(ou).nullish(),
	relatedSnippets: F(cu).nullish(),
	editHistory: F(lu).nullish(),
	userActions: F(uu).nullish(),
	openFiles: F(du).nullish(),
	diagnostics: F(pu).nullish(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), hu = I({
	sessionId: W,
	uri: k(),
	version: j(),
	position: Lc,
	selection: Rc.nullish(),
	triggerKind: au,
	context: mu.nullish(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), gu = I({
	sessionId: W,
	_meta: V(z(k(), P()).nullish(), () => void 0)
});
I({
	id: Eo,
	method: k(),
	params: L([
		Pl,
		Fl,
		Il,
		Ll,
		Rl,
		zl,
		Kl,
		ql,
		Jl,
		Yl,
		Xl,
		Zl,
		Ql,
		$l,
		eu,
		tu,
		iu,
		hu,
		gu,
		ws,
		Es
	]).nullish()
});
var _u = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), vu = I({
	content: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), yu = I({
	optionId: qo,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), bu = I({
	outcome: L([I({ outcome: B("cancelled") }), yu.and(I({ outcome: B("selected") }))]),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), xu = I({
	terminalId: Ho,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Su = I({
	exitCode: V(M().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	signal: V(k().nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Cu = I({
	output: k(),
	truncated: N(),
	exitStatus: V(Su.nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), wu = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), Tu = I({
	exitCode: V(M().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	signal: V(k().nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Eu = I({ _meta: V(z(k(), P()).nullish(), () => void 0) }), Du = L([
	k(),
	j(),
	j(),
	N(),
	F(k())
]), Ou = I({ content: z(k(), Du).nullish() });
L([I({
	id: Eo,
	result: L([
		_u,
		vu,
		bu,
		xu,
		Cu,
		wu,
		Tu,
		Eu,
		To(R(L([
			Ou.and(I({ action: B("accept") })),
			I({ action: B("decline") }),
			I({ action: B("cancel") }),
			wo(I({ action: k() }), "action", [
				"accept",
				"cancel",
				"decline"
			])
		]), I({ _meta: V(z(k(), P()).nullish(), () => void 0) })), "action", [
			"accept",
			"cancel",
			"decline"
		]),
		I({
			connectionId: Cs,
			_meta: V(z(k(), P()).nullish(), () => void 0)
		}),
		I({ _meta: V(z(k(), P()).nullish(), () => void 0) }),
		qc,
		Kc
	])
}), I({
	id: Eo,
	error: Jc
})]);
var ku = I({
	sessionId: W,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Au = I({
	sessionId: W,
	uri: k(),
	languageId: k(),
	version: j(),
	text: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), ju = I({
	range: Rc.nullish(),
	text: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Mu = I({
	sessionId: W,
	uri: k(),
	version: j(),
	contentChanges: H(U(ju), () => []),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Nu = I({
	sessionId: W,
	uri: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Pu = I({
	sessionId: W,
	uri: k(),
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Fu = I({
	sessionId: W,
	uri: k(),
	version: j(),
	position: Lc,
	visibleRange: Rc,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Iu = I({
	sessionId: W,
	id: Ic,
	_meta: V(z(k(), P()).nullish(), () => void 0)
}), Lu = I({
	sessionId: W,
	id: Ic,
	reason: V(L([
		B("rejected"),
		B("ignored"),
		B("replaced"),
		B("cancelled")
	]).nullish(), () => void 0),
	_meta: V(z(k(), P()).nullish(), () => void 0)
});
I({
	method: k(),
	params: L([
		ku,
		Au,
		Mu,
		Nu,
		Pu,
		Fu,
		Iu,
		Lu,
		yl,
		bl
	]).nullish()
}), I({
	requestId: Eo,
	_meta: V(z(k(), P()).nullish(), () => void 0)
});
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/jsonrpc.js
var Ru = "$/cancel_request";
function zu(e) {
	return Uu(e) && "id" in e && typeof e.method == "string" && Wu(e.id);
}
function Bu(e) {
	if (!Uu(e) || "method" in e || !("id" in e) || !Wu(e.id)) return !1;
	let t = Object.hasOwn(e, "result"), n = Object.hasOwn(e, "error");
	return t === n ? !1 : !n || Ju(e.error);
}
function Vu(e) {
	return Uu(e) && !("id" in e) && typeof e.method == "string";
}
function Hu(e) {
	return typeof e == "object" && !!e;
}
function Uu(e) {
	return Hu(e) && e.jsonrpc === "2.0";
}
function Wu(e) {
	return e === null || typeof e == "string" || typeof e == "number" && Number.isFinite(e);
}
function Gu(e) {
	return Hu(e) && !("method" in e) && ("id" in e || "result" in e || "error" in e);
}
function Ku(e) {
	let t = !1, n = !1, r = !1, i = !1;
	for (let a of e) t ||= zu(a) || Vu(a), n ||= Bu(a), Hu(a) && (r ||= "method" in a, i ||= "result" in a || "error" in a);
	return t ? !1 : n ? !0 : i && !r;
}
function qu(e) {
	if (!(!Hu(e) || !Wu(e.requestId))) return e.requestId;
}
function Ju(e) {
	return Hu(e) && typeof e.code == "number" && Number.isInteger(e.code) && typeof e.message == "string";
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
function Yu(e) {
	let t = Promise.reject(e);
	return t.catch(() => {}), t;
}
function Xu(e) {
	if (e instanceof Error || typeof e == "object" && e && "message" in e && typeof e.message == "string") return e.message;
}
function Zu(e) {
	return typeof e == "object" && !!e && "name" in e && e.name === "ZodError" && "issues" in e && Array.isArray(e.issues) && "format" in e && typeof e.format == "function";
}
function Qu(e) {
	if (e instanceof K) return e.toResult();
	if (Zu(e)) return K.invalidParams(e.format()).toResult();
	let t = Xu(e);
	try {
		return K.internalError(t ? JSON.parse(t) : {}).toResult();
	} catch {
		return K.internalError({ details: t }).toResult();
	}
}
function $u(e) {
	return e instanceof K && e.code === -32800 ? e : K.requestCancelled(e);
}
function ed(e, t) {
	let n = td(e, t);
	return n ? n.toResult() : Qu(e);
}
function td(e, t) {
	if (!(!t.aborted || !nd(e))) return $u(t.reason);
}
function nd(e) {
	if (typeof e != "object" || !e) return !1;
	let t = e;
	return t.name === "AbortError" || t.code === "ABORT_ERR";
}
var rd = class {
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
		return this.didRespond ? Yu(/* @__PURE__ */ Error("JSON-RPC request already responded")) : (this.didRespond = !0, this.sendResult(e).finally(() => {
			this.finishRequest?.();
		}));
	}
}, id = /* @__PURE__ */ new WeakMap(), ad = class {
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
}, od = class {
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
}, sd = class {
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
	context = new od(this);
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
		return new cd();
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
		return new ad(() => {
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
		if (this.abortController.signal.aborted) return Yu(this.closedReason());
		let i = this.prepareRequest(e, t, n, r);
		return this.sendWireMessage(i.message).catch(() => {}), r.cancellationSignal?.aborted && i.cancel(), i.response;
	}
	sendBatch(e) {
		if (this.abortController.signal.aborted) return Yu(this.closedReason());
		if (!this.allowBatches) return Yu(/* @__PURE__ */ TypeError("JSON-RPC batches are not supported on this connection"));
		if (e.length === 0) return Yu(/* @__PURE__ */ TypeError("JSON-RPC batch must contain at least one entry"));
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
		return this.sendNotification(Ru, { requestId: e });
	}
	sendNotification(e, t) {
		return this.abortController.signal.aborted ? Yu(this.closedReason()) : this.sendWireMessage({
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
		if (!zu(e) && !Vu(e) && !Gu(e)) {
			this.sendWireMessage(ld(K.invalidRequest(e))).catch(() => {});
			return;
		}
		this.receiveMessage(e);
	}
	receiveBatch(e) {
		if (e.length === 0) {
			this.sendWireMessage(ld(K.invalidRequest(e))).catch(() => {});
			return;
		}
		let t = Ku(e), n = t ? 0 : e.reduce((e, t) => e + +!Vu(t), 0), r = e.reduce((e, t) => e + +!!Vu(t), 0), i = !1, a = [], o = async () => {
			i || n !== 0 || r !== 0 || a.length === 0 || (i = !0, await this.sendWireMessage(a));
		}, s = async (e) => {
			a.push(e), --n, await o();
		};
		for (let n of e) {
			if (t) {
				Gu(n) && this.receiveMessage(n);
				continue;
			}
			if (!zu(n) && !Vu(n)) {
				s(ld(K.invalidRequest(n))).catch(() => {});
				continue;
			}
			let i = this.receiveMessage(n, zu(n) ? s : void 0, e.length);
			Vu(n) && i.finally(() => {
				--r, o().catch((e) => this.close(e));
			});
		}
	}
	receiveMessage(e, t, n) {
		return this.abortController.signal.aborted ? Promise.resolve() : Hu(e) ? "method" in e ? ("id" in e || this.handleProtocolNotification(e), this.processIncomingMessage(this.toIncomingMessage(e, t, n)).catch((e) => this.close(e))) : ("id" in e ? this.handleResponse(e) : console.error("Invalid message", { message: e }), Promise.resolve()) : (console.error("Invalid message", { message: e }), Promise.resolve());
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
			if (t.kind === "request" && !t.responder.responded) await t.responder.respondWithResult(ed(n, t.responder.signal));
			else {
				let t = Qu(n);
				"error" in t && console.error("Error handling notification", e.raw, t.error);
			}
		}
	}
	toIncomingMessage(e, t, n) {
		if ("id" in e) {
			let r = new AbortController();
			this.incomingRequests.set(e.id, r);
			let i = new rd(e.id, (n) => {
				let r = {
					jsonrpc: "2.0",
					id: e.id,
					...n
				};
				return t ? t(r) : this.sendWireMessage(r);
			}, r.signal, () => {
				this.incomingRequests.get(e.id) === r && this.incomingRequests.delete(e.id);
			});
			return n !== void 0 && id.set(i, n), {
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
			if (this.pendingResponses.delete(e.id), t.cleanup?.(), !Bu(e)) t.reject(K.invalidRequest(e));
			else if ("result" in e) t.resolve(e.result);
			else {
				let { code: n, message: r, data: i } = e.error;
				t.reject(new K(n, r, i));
			}
		} else console.error("Got response to unknown request", e.id);
	}
	handleProtocolNotification(e) {
		if (e.method !== Ru) return;
		let t = qu(e.params);
		if (t === void 0) return;
		let n = this.incomingRequests.get(t);
		!n || n.signal.aborted || n.abort(K.requestCancelled({ requestId: t }));
	}
	closedReason() {
		return this.abortController.signal.reason ?? /* @__PURE__ */ Error("ACP connection closed");
	}
	async sendWireMessage(e) {
		return this.abortController.signal.aborted ? Yu(this.closedReason()) : (this.writeQueue = this.writeQueue.then(async () => {
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
}, cd = class {
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
		return new sd(e, this.handlers, t);
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
function ld(e) {
	return {
		jsonrpc: "2.0",
		id: null,
		error: e.toErrorResponse()
	};
}
_s.and(I({ mode: B("form") })).and(I({ message: k() })), ys.and(I({ mode: B("url") })).and(I({ message: k() })), L([ns, rs]).and(I({ message: k() })), ss.and(I({ type: B("string") })), cs.and(I({ type: B("number") })), ls.and(I({ type: B("integer") })), us.and(I({ type: B("boolean") })), ms.and(I({ type: B("array") })), ds.and(I({ type: B("string") })), Ou.and(I({ action: B("accept") })), I({ action: B("decline") }), I({ action: B("cancel") });
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/acp.js
function q(e) {
	return e ?? {};
}
function ud(e) {
	return typeof e == "object" && !!e && "readable" in e && "writable" in e;
}
function dd() {
	let e = new TransformStream(), t = new TransformStream();
	return [{
		readable: t.readable,
		writable: e.writable
	}, {
		readable: e.readable,
		writable: t.writable
	}];
}
var fd = {
	agent: {
		initialize: m.initialize,
		authenticate: m.authenticate,
		logout: m.logout,
		providers: {
			list: m.providers_list,
			set: m.providers_set,
			disable: m.providers_disable
		},
		session: {
			new: m.session_new,
			load: m.session_load,
			list: m.session_list,
			delete: m.session_delete,
			fork: m.session_fork,
			resume: m.session_resume,
			close: m.session_close,
			setMode: m.session_set_mode,
			setConfigOption: m.session_set_config_option,
			prompt: m.session_prompt,
			cancel: m.session_cancel
		},
		nes: {
			start: m.nes_start,
			suggest: m.nes_suggest,
			accept: m.nes_accept,
			reject: m.nes_reject,
			close: m.nes_close
		},
		document: {
			didOpen: m.document_did_open,
			didChange: m.document_did_change,
			didClose: m.document_did_close,
			didSave: m.document_did_save,
			didFocus: m.document_did_focus
		}
	},
	client: {
		session: {
			requestPermission: h.session_request_permission,
			update: h.session_update
		},
		fs: {
			writeTextFile: h.fs_write_text_file,
			readTextFile: h.fs_read_text_file
		},
		terminal: {
			create: h.terminal_create,
			output: h.terminal_output,
			release: h.terminal_release,
			waitForExit: h.terminal_wait_for_exit,
			kill: h.terminal_kill
		},
		elicitation: {
			create: h.elicitation_create,
			complete: h.elicitation_complete
		}
	},
	protocol: { cancelRequest: ae.cancel_request }
}, pd = Symbol("startActiveSession"), md = class {
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
}, hd = class e extends md {
	constructor(e, t) {
		super(e, t);
	}
	static create(t, n) {
		return new e(t, n);
	}
	request(e, t, n) {
		let r = Fd[e];
		return this.sendRequest(e, t, r?.mapResponse, n);
	}
	notify(e, t) {
		return this.sendNotification(e, t);
	}
}, gd = class e extends md {
	constructor(e, t) {
		super(e, t);
	}
	static create(t, n) {
		return new e(t, n);
	}
	[pd](e, t) {
		return this.sendRequest(m.session_new, e, (e) => this.attachSession(e), t);
	}
	buildSession(e) {
		return typeof e == "string" ? wd.create(this, {
			cwd: e,
			mcpServers: []
		}) : wd.create(this, e);
	}
	attachSession(e) {
		let t = new Sd(), n = this.connectionContext.signal, r = () => {
			t.fail(n.reason ?? /* @__PURE__ */ Error("ACP connection closed"));
		};
		n.aborted ? r() : n.addEventListener("abort", r);
		let i = Vd(this.connectionContext).attach(e, t), a = new ad(() => {
			n.removeEventListener("abort", r);
		});
		return Td.create(this, e, t, [i, a]);
	}
	request(e, t, n) {
		let r = Pd[e];
		return this.sendRequest(e, t, r?.mapResponse, n);
	}
	notify(e, t) {
		return this.sendNotification(e, t);
	}
}, _d = class {
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
}, vd = class extends _d {
	connectHandlers;
	client;
	didStartConnectHandlers = !1;
	constructor(e, t = []) {
		super(e), this.connectHandlers = t, this.client = hd.create(e.getContext());
	}
	startConnectHandlers() {
		this.didStartConnectHandlers || (this.didStartConnectHandlers = !0, Hd(this, this.connectHandlers));
	}
}, yd = class extends _d {
	connectHandlers;
	agent;
	didStartConnectHandlers = !1;
	constructor(e, t = []) {
		super(e), this.connectHandlers = t, this.agent = gd.create(e.getContext());
	}
	startConnectHandlers() {
		this.didStartConnectHandlers || (this.didStartConnectHandlers = !0, Hd(this, this.connectHandlers));
	}
};
function bd(e, t = []) {
	return new vd(e, t);
}
function xd(e, t = []) {
	return new yd(e, t);
}
var Sd = class {
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
function Cd(e) {
	return {
		...e,
		additionalDirectories: e.additionalDirectories ? [...e.additionalDirectories] : void 0,
		mcpServers: [...e.mcpServers]
	};
}
var wd = class e {
	cx;
	request;
	constructor(e, t) {
		this.cx = e, this.request = Cd(t);
	}
	static create(t, n) {
		return new e(t, n);
	}
	toRequest() {
		return Cd(this.request);
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
		return this.cx[pd](this.toRequest(), e);
	}
	async withSession(e) {
		let t = await this.start();
		try {
			return await e(t);
		} finally {
			t.dispose();
		}
	}
}, Td = class e {
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
		let n = this.cx.request(m.session_prompt, {
			sessionId: this.sessionId,
			prompt: this.promptBlocks(e)
		}, t);
		return n.then((e) => {
			this.updates.enqueue({
				kind: "stop",
				response: e,
				stopReason: e.stopReason
			});
		}, (e) => {
			this.updates.reject(e);
		}), n;
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
function Ed(e, t) {
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
function Dd(e, t, n, r) {
	e.onReceiveRequest(t.method, (e) => Ed(t.params, e), async (e, i, a) => {
		let o = await r(n(e, a, i.signal, i.id));
		await i.respond(t.mapResponse ? t.mapResponse(o) : o);
	});
}
function Od(e, t, n, r) {
	e.onReceiveNotification(t.method, (e) => Ed(t.params, e), (e, t) => r(n(e, t, t.signal)));
}
function kd(e) {
	let t = {};
	for (let n of Object.values(e)) t[n.method] = n;
	return t;
}
var Ad = {
	initialize: J(m.initialize, Pl),
	newSession: J(m.session_new, Kl),
	loadSession: J(m.session_load, ql, q),
	unstable_forkSession: J(m.session_fork, Xl),
	listSessions: J(m.session_list, Jl),
	deleteSession: J(m.session_delete, Yl, q),
	resumeSession: J(m.session_resume, Zl),
	closeSession: J(m.session_close, Ql, q),
	setSessionMode: J(m.session_set_mode, $l, q),
	setSessionConfigOption: J(m.session_set_config_option, eu),
	authenticate: J(m.authenticate, Fl, q),
	unstable_listProviders: J(m.providers_list, Il),
	unstable_setProvider: J(m.providers_set, Ll, q),
	unstable_disableProvider: J(m.providers_disable, Rl, q),
	logout: J(m.logout, zl, q),
	prompt: J(m.session_prompt, tu),
	unstable_startNes: J(m.nes_start, iu),
	unstable_suggestNes: J(m.nes_suggest, hu),
	unstable_closeNes: J(m.nes_close, gu, q)
}, jd = {
	cancel: Y(m.session_cancel, ku),
	unstable_didOpenDocument: Y(m.document_did_open, Au),
	unstable_didChangeDocument: Y(m.document_did_change, Mu),
	unstable_didCloseDocument: Y(m.document_did_close, Nu),
	unstable_didSaveDocument: Y(m.document_did_save, Pu),
	unstable_didFocusDocument: Y(m.document_did_focus, Fu),
	unstable_acceptNes: Y(m.nes_accept, Iu),
	unstable_rejectNes: Y(m.nes_reject, Lu)
}, Md = {
	requestPermission: J(h.session_request_permission, Yo),
	writeTextFile: J(h.fs_write_text_file, Do, q),
	readTextFile: J(h.fs_read_text_file, Oo),
	createTerminal: J(h.terminal_create, Zo),
	terminalOutput: J(h.terminal_output, Qo),
	releaseTerminal: J(h.terminal_release, $o, q),
	waitForTerminalExit: J(h.terminal_wait_for_exit, es),
	killTerminal: J(h.terminal_kill, ts, q),
	createElicitation: J(h.elicitation_create, bs)
}, Nd = {
	sessionUpdate: Y(h.session_update, _l),
	completeElicitation: Y(h.elicitation_complete, vl)
}, Pd = kd(Ad);
kd(jd);
var Fd = kd(Md), Id = kd(Nd);
function Ld(e, t, n, r) {
	return {
		params: e,
		requestId: r,
		signal: n,
		agent: t
	};
}
function Rd(e, t, n) {
	return {
		params: e,
		signal: n,
		agent: t
	};
}
var zd = class {
	activeSessions = /* @__PURE__ */ new Map();
	handleMessage(e) {
		if (e.kind !== "notification" || e.method !== h.session_update) return G.no(e);
		let t = _l.parse(e.params), n = {
			kind: "session_update",
			notification: t,
			update: t.update
		}, r = this.activeSessions.get(t.sessionId);
		if (r && r.size > 0) for (let e of r) e.enqueue(n);
		return G.no(e);
	}
	attach(e, t) {
		let n = this.activeSessions.get(e.sessionId) ?? /* @__PURE__ */ new Set();
		return n.add(t), this.activeSessions.set(e.sessionId, n), new ad(() => {
			n.delete(t), n.size === 0 && this.activeSessions.delete(e.sessionId);
		});
	}
}, Bd = /* @__PURE__ */ new WeakMap();
function Vd(e) {
	let t = Bd.get(e);
	return t || (t = new zd(), Bd.set(e, t)), t;
}
function Hd(e, t) {
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
var Ud = Symbol("appBuilder"), Wd = Symbol("runAgentConnectHandlers"), Gd = Symbol("runClientConnectHandlers"), Kd = { allowBatches: !1 };
function qd(e) {
	return new Jd(e);
}
var Jd = class {
	builder = sd.builder();
	connectHandlers = [];
	constructor(e = {}) {
		e.name && this.builder.name(e.name), this.builder.withHandler({
			handleMessage: (e, t) => Vd(t).handleMessage(e),
			describe: () => "client-session-update-router"
		});
	}
	[Ud]() {
		return this.builder;
	}
	[Gd](e) {
		Hd(e, this.connectHandlers);
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
		let r = Fd[e];
		if (!r) throw Error(`Unknown ACP request method '${e}'. Pass a params parser for custom methods.`);
		return this.request(r, t);
	}
	onNotification(e, t, n) {
		if (n) return this.notification({
			method: e,
			params: t
		}, n);
		let r = Id[e];
		if (!r) throw Error(`Unknown ACP notification method '${e}'. Pass a params parser for custom methods.`);
		return this.notification(r, t);
	}
	request(e, t) {
		return Dd(this.builder, e, (e, t, n, r) => Ld(e, gd.create(t, r), n, r), t), this;
	}
	notification(e, t) {
		return Od(this.builder, e, (e, t, n) => Rd(e, gd.create(t), n), t), this;
	}
	connectConnection(e) {
		if (ud(e)) {
			let t = this.openStreamConnection(e);
			return this[Gd](t.connection), t;
		}
		let [t, n] = dd(), r = e[Ud]().connect(n, Kd), i = bd(r), a = this.openStreamConnection(t);
		a.rawConnection.closed.then(() => i.close()), r.closed.then(() => a.connection.close());
		try {
			e[Wd](i), this[Gd](a.connection);
		} catch (e) {
			throw i.close(e), a.connection.close(e), e;
		}
		return a;
	}
	openStreamConnection(e) {
		let t = this.builder.connect(e, Kd);
		return {
			rawConnection: t,
			connection: xd(t, this.connectHandlers)
		};
	}
};
m.initialize, m.authenticate, m.providers_list, m.providers_set, m.providers_disable, m.session_new, m.session_load, m.session_set_mode, m.session_set_config_option, m.session_prompt, m.session_list, m.session_delete, m.session_fork, m.session_resume, m.session_close, m.logout, m.nes_start, m.nes_suggest, m.nes_close, m.session_cancel, m.nes_accept, m.nes_reject, m.document_did_open, m.document_did_change, m.document_did_close, m.document_did_save, m.document_did_focus, h.session_request_permission, h.fs_write_text_file, h.fs_read_text_file, h.terminal_create, h.terminal_output, h.terminal_release, h.terminal_wait_for_exit, h.terminal_kill, h.elicitation_create, h.session_update, h.elicitation_complete;
//#endregion
//#region src/core/protocol/normalize.ts
var Yd = 1e3, Xd = 64, Zd = 256, X = 16384, Qd = 256, $d = 1048576, ef = 8388608, tf = 1048576, nf = 4096, rf = 4194304, af = 4096, of = 16;
function Z(e) {
	return typeof e == "object" && !!e && !Array.isArray(e);
}
function Q(e, t = X) {
	return typeof e == "string" ? jf(e, t) : void 0;
}
function sf(e) {
	let t = Q(e, X);
	if (t) try {
		let e = new URL(t).protocol;
		return e === "http:" || e === "https:" ? t : void 0;
	} catch {
		return;
	}
}
function cf(e, t = Zd) {
	return Array.isArray(e) ? e.slice(0, t).filter(Z) : [];
}
function lf(e) {
	return Array.isArray(e) ? e.slice(0, Qd).flatMap((e) => {
		let t = wf(e);
		return t ? [t] : [];
	}) : [];
}
function uf(e) {
	let t = kf(e, { nodes: af }, 0);
	return Z(t) ? t : void 0;
}
function df(e) {
	return cf(e).map((e, t) => ({
		id: Q(e.methodId) ?? Q(e.id) ?? `auth-${t}`,
		name: Q(e.name) ?? Q(e.title) ?? `Authentication ${t + 1}`,
		...Q(e.description) ? { description: Q(e.description) } : {},
		type: Q(e.type) ?? "agent",
		raw: uf(e) ?? {}
	}));
}
function ff(e) {
	return cf(e).flatMap((e) => {
		let t = Q(e.name);
		if (!t) return [];
		let n = Z(e.input) ? e.input : void 0;
		return [{
			name: t,
			description: Q(e.description) ?? "",
			...n && Q(n.hint) ? { inputHint: Q(n.hint) } : {}
		}];
	});
}
function pf(e) {
	return cf(e).flatMap((e) => {
		let t = Q(e.configId) ?? Q(e.id);
		if (!t) return [];
		let n = Q(e.type), r = e.currentValue, i = n === "boolean" || typeof r == "boolean" ? "boolean" : n === "select" || Array.isArray(e.options) ? "select" : "unknown", a = typeof r == "boolean" ? r : Q(r) ?? "", o = cf(e.options).flatMap((e) => {
			let t = Q(e.value);
			return t ? [{
				value: t,
				name: Q(e.name) ?? t,
				...Q(e.description) ? { description: Q(e.description) } : {}
			}] : [];
		});
		return [{
			id: t,
			name: Q(e.name) ?? t,
			...Q(e.description) ? { description: Q(e.description) } : {},
			...Q(e.category) ? { category: Q(e.category) } : {},
			type: i,
			currentValue: a,
			...o.length ? { options: o } : {}
		}];
	});
}
function mf(e) {
	if (!Z(e)) return [];
	let t = cf(e.availableModes), n = Q(e.currentModeId) ?? "";
	return t.length ? [{
		id: "mode",
		name: "Mode",
		category: "mode",
		type: "select",
		currentValue: n,
		options: t.flatMap((e) => {
			let t = Q(e.id);
			return t ? [{
				value: t,
				name: Q(e.name) ?? t,
				...Q(e.description) ? { description: Q(e.description) } : {}
			}] : [];
		})
	}] : [];
}
function hf(e) {
	if (!Z(e)) return { sessions: [] };
	let t = cf(e.sessions).flatMap((e) => {
		let t = Q(e.sessionId);
		return t ? [{
			sessionId: t,
			...Q(e.title) ? { title: Q(e.title) } : {},
			...Q(e.updatedAt) ? { updatedAt: Q(e.updatedAt) } : {},
			...Q(e.cwd) ? { cwd: Q(e.cwd) } : {}
		}] : [];
	}), n = Q(e.nextCursor);
	return {
		sessions: t,
		...n ? { nextCursor: n } : {}
	};
}
function gf(e) {
	if (!Z(e) || !Pf(e.used) || !Pf(e.size)) return;
	let t = Z(e.cost) ? Q(e.cost.currency) : void 0, n = Z(e.cost) && Pf(e.cost.amount) && t !== void 0 ? {
		amount: e.cost.amount,
		currency: t
	} : void 0;
	return {
		used: e.used,
		size: e.size,
		...n ? { cost: n } : {}
	};
}
var _f = class {
	#e = [];
	#t = 0;
	#n = /* @__PURE__ */ new Map();
	#r;
	#i;
	#a = /* @__PURE__ */ new Set();
	#o = /* @__PURE__ */ new Set();
	#s;
	#c = /* @__PURE__ */ new Map();
	get activities() {
		return this.#e;
	}
	reset() {
		this.#e = [], this.#n.clear(), this.#r = void 0, this.#i = void 0, this.#a.clear(), this.#o.clear(), this.#s = void 0, this.#c.clear();
	}
	beginTurn() {
		this.#n.clear(), this.#i = void 0;
	}
	addNotice(e) {
		let t = this.#e.filter((e) => e.type === "notice").length - Xd + 1;
		t > 0 && (this.#e = this.#e.filter((e) => e.type !== "notice" || t <= 0 || (--t, !1))), this.#S(e);
	}
	addUserMessage(e, t, n) {
		let r = vf(n), i = lf(e), a = `local-user-${++this.#t}`;
		return this.#S({
			type: "message",
			id: a,
			role: "user",
			content: i,
			...r === void 0 ? {} : { timestamp: r },
			...t ? { pending: !0 } : {}
		}), this.#i = r, this.#r = t ? a : void 0, a;
	}
	markFinalAnswer(e) {
		let t = vf(e);
		if (t !== void 0) for (let e = this.#e.length - 1; e >= 0; --e) {
			let n = this.#e[e];
			if (n?.type === "message") {
				if (n.role === "user") return;
				if (n.role === "assistant") {
					this.#_(n.id, () => ({
						...n,
						timestamp: Math.max(t, this.#i ?? t)
					}));
					return;
				}
			}
		}
	}
	finishTurn(e) {
		e !== void 0 && this.markFinalAnswer(e), this.#r && this.#_(this.#r, (e) => {
			if (e.type !== "message") return e;
			let { pending: t, ...n } = e;
			return n;
		}), this.#r = void 0;
	}
	finalizeReplay() {
		this.#y();
		let e = [];
		for (let t of this.#e) t.type !== "message" || t.role !== "user" || this.#o.has(t.id) || p(t.content).status === "malformed" && (this.#o.add(t.id), e.push({
			code: "MALFORMED_USER_MESSAGE_ENVELOPE",
			message: "A restored user-message envelope was incomplete; retained the Agent history unchanged"
		}));
		return e.length ? { diagnostics: e } : {};
	}
	markUserAccepted(e = []) {
		if (this.#r) {
			this.#_(this.#r, (e) => e.type === "message" ? {
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
				this.#S(e);
			}
		}
	}
	reduce(e, t) {
		if (!Z(e) || typeof e.sessionUpdate != "string") return { unsupported: "invalid_update" };
		let n = Q(e.sessionUpdate) ?? "";
		if (this.#r && (n === "user_message_chunk" || n === "user_message")) return {};
		switch (n) {
			case "user_message_chunk":
			case "agent_message_chunk":
			case "agent_thought_chunk": {
				let r = n === "user_message_chunk" ? "user" : n === "agent_message_chunk" ? "assistant" : "thought";
				return this.#l(r, Q(e.messageId), e.content, t), {};
			}
			case "user_message":
			case "agent_message":
			case "agent_thought": {
				let t = n === "user_message" ? "user" : n === "agent_message" ? "assistant" : "thought";
				return this.#u(t, Q(e.messageId), e), {};
			}
			case "tool_call":
			case "tool_call_update": return this.#d(e), {};
			case "tool_call_content_chunk": return this.#f(e), {};
			case "plan":
			case "plan_update": return this.#p(e), {};
			case "plan_removed": return this.#v(`plan:${Q(e.planId) ?? "primary"}`), {};
			case "terminal_update": return this.#m(e), {};
			case "terminal_output_chunk": return this.#h(e), {};
			case "available_commands_update": return { commands: ff(e.availableCommands) };
			case "config_option_update": return { configOptions: pf(e.configOptions) };
			case "current_mode_update": return {};
			case "session_info_update": return { sessionTitle: Object.hasOwn(e, "title") ? Q(e.title) ?? null : void 0 };
			case "usage_update": return { usage: gf(e) };
			case "state_update": {
				let t = Q(e.state);
				return t === "running" || t === "requires_action" || t === "idle" ? {
					state: t,
					...Q(e.stopReason) ? { stopReason: Q(e.stopReason) } : {}
				} : { unsupported: `state:${t ?? "missing"}` };
			}
			default: return { unsupported: n };
		}
	}
	#l(e, t, n, r) {
		let i = t;
		if (!i && r === 1 && (i = this.#n.get(e) ?? `v1-${e}-${++this.#t}`, this.#n.set(e, i)), !i) return;
		let a = yf(e, i);
		if (this.#s && (e !== "user" || this.#s !== a) && this.#y(), e === "user" && this.#a.has(a)) return;
		let o = this.#e.find((e) => e.type === "message" && e.id === a), s = wf(n);
		s && (o?.type === "message" ? this.#_(a, () => ({
			...o,
			content: Sf(o.content, s)
		})) : this.#S({
			type: "message",
			id: a,
			role: e,
			content: [s]
		}), e === "user" && (this.#s = a));
	}
	#u(e, t, n) {
		if (!t) return;
		this.#y();
		let r = yf(e, t), i = this.#e.find((e) => e.type === "message" && e.id === r), a = Object.hasOwn(n, "content") ? lf(n.content) : i?.type === "message" ? i.content : [], o = e === "user" ? p(a) : void 0, s = o?.status === "restored" ? o.content : a;
		i?.type === "message" ? this.#_(r, () => ({
			...i,
			role: e,
			content: s
		})) : this.#S({
			type: "message",
			id: r,
			role: e,
			content: s
		}), o?.status === "restored" && this.#b(r, o);
	}
	#d(e) {
		let t = Q(e.toolCallId);
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
			...Object.hasOwn(e, "title") ? { title: Q(e.title) ?? "Tool" } : {},
			...Object.hasOwn(e, "kind") && Q(e.kind) ? { kind: Q(e.kind) } : {},
			...Object.hasOwn(e, "status") ? { status: Q(e.status) ?? "pending" } : {},
			...Object.hasOwn(e, "content") ? { content: Ef(e.content) } : {},
			...Object.hasOwn(e, "locations") ? { locations: Ef(e.locations).filter(Z) } : {},
			...Object.hasOwn(e, "rawInput") ? { rawInput: Df(e.rawInput) } : {},
			...Object.hasOwn(e, "rawOutput") ? { rawOutput: Df(e.rawOutput) } : {}
		}, s = bf(o), c = {
			...o,
			...s ? { subagent: s } : {}
		};
		this.#g(n, c);
	}
	#f(e) {
		let t = Q(e.toolCallId);
		if (!t || !Object.hasOwn(e, "content")) return;
		let n = `tool:${t}`, r = this.#e.find((e) => e.type === "tool" && e.id === n), i = r?.type === "tool" ? r : {
			type: "tool",
			id: n,
			title: "Tool",
			status: "pending",
			content: [],
			locations: []
		};
		i.content.length >= Zd || this.#g(n, {
			...i,
			content: Ef([...i.content, e.content])
		});
	}
	#p(e) {
		let t = Z(e.plan) ? e.plan : e, n = `plan:${Q(t.planId) ?? "primary"}`, r = {
			type: "plan",
			id: n,
			entries: cf(t.entries).map((e) => ({
				content: Q(e.content) ?? "",
				...Q(e.priority) ? { priority: Q(e.priority) } : {},
				status: Q(e.status) ?? "pending"
			}))
		};
		this.#g(n, r);
	}
	#m(e) {
		let t = Q(e.terminalId);
		if (!t) return;
		let n = `terminal:${t}`;
		if (Object.hasOwn(e, "output") && Z(e.output) && typeof e.output.data == "string") {
			let n = new TextDecoder(), r = Cf(e.output.data).subarray(0, rf), i = Af(n.decode(r, { stream: !0 }), tf);
			this.#c.set(t, {
				decoder: n,
				output: i,
				chunks: 1,
				decodedBytes: r.byteLength
			});
		}
		let r = this.#e.find((e) => e.type === "terminal" && e.id === n), i = Array.isArray(e.command) ? e.command.filter((e) => typeof e == "string").join(" ") : Q(e.command), a = this.#c.get(t)?.output ?? "", o = {
			type: "terminal",
			id: n,
			title: i ?? (r?.type === "terminal" ? r.title : "Terminal"),
			output: a,
			exited: Object.hasOwn(e, "exitStatus") ? e.exitStatus !== null : r?.type === "terminal" && r.exited
		};
		this.#g(n, o);
	}
	#h(e) {
		let t = Q(e.terminalId), n = Q(e.data);
		if (!t || !n) return;
		let r = this.#c.get(t) ?? {
			decoder: new TextDecoder(),
			output: "",
			chunks: 0,
			decodedBytes: 0
		};
		if (r.chunks >= nf || r.decodedBytes >= rf) return;
		let i = rf - r.decodedBytes, a = Cf(n).subarray(0, i);
		r.chunks += 1, r.decodedBytes += a.byteLength, r.output = Af(r.output + r.decoder.decode(a, { stream: !0 }), tf), this.#c.set(t, r);
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
		this.#g(o, c);
	}
	#g(e, t) {
		let n = this.#e.findIndex((t) => t.id === e);
		if (n < 0) {
			this.#S(t);
			return;
		}
		this.#e = this.#e.map((e, r) => r === n ? t : e);
	}
	#_(e, t) {
		this.#e = this.#e.map((n) => n.id === e ? t(n) : n);
	}
	#v(e) {
		this.#e = this.#e.filter((t) => t.id !== e);
	}
	#y() {
		let e = this.#s;
		if (this.#s = void 0, !e || this.#a.has(e)) return;
		let t = this.#e.find((t) => t.id === e);
		if (t?.type !== "message" || t.role !== "user") return;
		let n = p(t.content);
		n.status === "restored" && this.#b(e, n);
	}
	#b(e, t) {
		this.#a.has(e) || (this.#a.add(e), this.#_(e, (e) => e.type === "message" ? {
			...e,
			content: t.content
		} : e), this.#x(e, t.context.map((e) => ({
			type: "context",
			id: `restored-context-${++this.#t}`,
			contextId: e.id,
			label: e.label,
			content: e.content
		}))));
	}
	#x(e, t) {
		if (!t.length) return;
		let n = this.#e.findIndex((t) => t.id === e);
		n < 0 || (this.#e = [
			...this.#e.slice(0, n + 1),
			...t,
			...this.#e.slice(n + 1)
		], this.#C());
	}
	#S(e) {
		this.#e = [...this.#e, e], this.#C();
	}
	#C() {
		let e = this.#e.filter((e) => e.type !== "notice").length - Yd;
		if (e <= 0) return;
		let t = [];
		this.#e = this.#e.filter((n) => n.type === "notice" || n.id === this.#r || e <= 0 || (--e, t.push(n), !1));
		for (let e of t) e.type === "terminal" && this.#c.delete(e.id.slice(9));
	}
};
function vf(e) {
	if (!(e === void 0 || !Number.isFinite(e) || e < 0 || Number.isNaN(new Date(e).valueOf()))) return e;
}
function yf(e, t) {
	return `message:${e}:${t}`;
}
function bf(e) {
	if (e.kind !== "think" || !Z(e.rawInput)) return;
	let t = Q(e.rawInput.subagent_type), n = Q(e.rawInput.description), r = Q(e.rawInput.prompt);
	if (!t || !n || !r) return;
	let i = Z(e.rawOutput) && Z(e.rawOutput.metadata) ? e.rawOutput.metadata : void 0, a = xf(i?.sessionId), o = xf(e.rawInput.task_id), s = a ?? o, c = e.rawInput.background === !0 || i?.background === !0;
	return {
		agent: t,
		...n ? { description: n } : {},
		...s ? { sessionId: s } : {},
		background: c
	};
}
function xf(e) {
	return typeof e == "string" && e.length > 0 && e.length <= X ? e : void 0;
}
function Sf(e, t) {
	let n = e.at(-1);
	return n?.type === "text" && typeof n.text == "string" && t.type === "text" && typeof t.text == "string" && n.annotations == null && n._meta == null && t.annotations == null && t._meta == null ? [...e.slice(0, -1), {
		type: "text",
		text: Af(n.text + t.text, $d)
	}] : e.length >= Qd ? [...e] : [...e, t];
}
function Cf(e) {
	try {
		if (typeof globalThis.atob == "function") {
			let t = globalThis.atob(e.slice(0, ef));
			return Uint8Array.from(t, (e) => e.charCodeAt(0));
		}
		return new Uint8Array(Buffer.from(e.slice(0, ef), "base64"));
	} catch {
		return /* @__PURE__ */ new Uint8Array();
	}
}
function wf(e) {
	if (!Z(e)) return;
	let t = Q(e.type, 128);
	if (!t) return;
	let n = Tf(e._meta), r = {
		type: t,
		...n
	};
	if (t === "text") {
		let t = Q(e.text, $d);
		return t === void 0 ? void 0 : {
			...r,
			type: "text",
			text: t
		};
	}
	if (t === "image" || t === "audio") {
		let n = Q(e.data, ef), i = Q(e.mimeType, 256);
		return n === void 0 || i === void 0 ? void 0 : {
			...r,
			type: t,
			data: n,
			mimeType: i
		};
	}
	if (t === "resource_link") {
		let t = n ? Q(e.uri, X) : Ff(e.uri), i = Q(e.name, X);
		return !t || !i ? void 0 : {
			...r,
			type: "resource_link",
			uri: t,
			name: i,
			...Q(e.title) ? { title: Q(e.title) } : {},
			...Q(e.description) ? { description: Q(e.description) } : {},
			...Q(e.mimeType, 256) ? { mimeType: Q(e.mimeType, 256) } : {},
			...typeof e.size == "number" && Number.isFinite(e.size) ? { size: e.size } : {}
		};
	}
	if (t === "resource" && Z(e.resource)) {
		let t = n ? Q(e.resource.uri, X) : Ff(e.resource.uri);
		return t ? {
			...r,
			type: "resource",
			resource: {
				uri: t,
				...Q(e.resource.mimeType, 256) ? { mimeType: Q(e.resource.mimeType, 256) } : {},
				...Q(e.resource.text, 1048576) === void 0 ? {} : { text: Q(e.resource.text, $d) },
				...Q(e.resource.blob, 8388608) === void 0 ? {} : { blob: Q(e.resource.blob, ef) }
			}
		} : void 0;
	}
	return r;
}
function Tf(e) {
	if (!Z(e)) return;
	let t = e["pretty-aui/context"];
	if (!(!Z(t) || t.version !== 1 || typeof t.id != "string" || !t.id.trim() || t.id.length > X || typeof t.label != "string" || !t.label.trim() || t.label.length > X)) return { _meta: { "pretty-aui/context": {
		version: 1,
		id: t.id,
		label: t.label
	} } };
}
function Ef(e) {
	if (!Array.isArray(e)) return [];
	let t = kf(e, { nodes: af }, 0);
	return Array.isArray(t) ? t : [];
}
function Df(e) {
	let t = kf(e, { nodes: af }, 0);
	return t === Of ? null : t;
}
var Of = Symbol("omit-structured-value");
function kf(e, t, n) {
	if (t.nodes <= 0 || n > of) return Of;
	if (--t.nodes, typeof e == "string") return jf(e, $d);
	if (e === null || typeof e == "boolean" || typeof e == "number" && Number.isFinite(e)) return e;
	if (Array.isArray(e)) {
		let r = [];
		for (let i of e.slice(0, Zd)) {
			let e = kf(i, t, n + 1);
			if (e !== Of && r.push(e), t.nodes <= 0) break;
		}
		return r;
	}
	if (Z(e)) {
		let r = {};
		for (let [i, a] of Object.entries(e).slice(0, Zd)) {
			let e = kf(a, t, n + 1);
			if (e !== Of && (r[jf(i, X)] = e), t.nodes <= 0) break;
		}
		return r;
	}
	return null;
}
function Af(e, t) {
	if (e.length <= t) return e;
	let n = e.length - t;
	return Nf(e.charCodeAt(n)) && (n += 1), e.slice(n);
}
function jf(e, t) {
	if (e.length <= t) return e;
	let n = t;
	return Mf(e.charCodeAt(n - 1)) && --n, e.slice(0, n);
}
function Mf(e) {
	return e >= 55296 && e <= 56319;
}
function Nf(e) {
	return e >= 56320 && e <= 57343;
}
function Pf(e) {
	return typeof e == "number" && Number.isFinite(e) && e >= 0 && !Object.is(e, -0);
}
function Ff(e) {
	let t = Q(e, X);
	if (t) try {
		let e = new URL(t).protocol;
		return e === "http:" || e === "https:" || e === "file:" ? t : void 0;
	} catch {
		return;
	}
}
//#endregion
//#region src/core/protocol/interactions.ts
function If(e) {
	return cf(e).map((e, t) => ({
		id: Q(e.optionId) ?? `option-${t}`,
		name: Q(e.name) ?? `Option ${t + 1}`,
		kind: Q(e.kind) ?? "unknown"
	}));
}
function Lf(e) {
	let t = Z(e) ? e : {}, n = t.mode === "form" || t.mode === "url" ? t.mode : "unknown", r = Q(t.elicitationId), i = uf(t.requestedSchema), a = sf(t.url);
	return {
		type: "elicitation",
		...r ? { elicitationId: r } : {},
		mode: n,
		message: Q(t.message) ?? "The agent needs more information.",
		...a ? { url: a } : {},
		...i ? { requestedSchema: i } : {}
	};
}
function Rf(e) {
	return { outcome: e };
}
function zf(e) {
	return e.action === "accept" ? {
		action: "accept",
		...e.content ? { content: Object.fromEntries(Object.entries(e.content).map(([e, t]) => [e, Array.isArray(t) ? [...t] : t])) } : {}
	} : { action: e.action };
}
//#endregion
//#region src/core/protocol/types.ts
function Bf(e, t, n, r) {
	if (!Gf(e.cwd)) throw $(`ACP cwd must be an absolute path: ${e.cwd}`, n, r);
	if (e.additionalDirectories?.some((e) => !Gf(e))) throw $("ACP additionalDirectories must contain only absolute paths", n, r);
	if (e.additionalDirectories?.length && !t.additionalDirectories) throw $("The agent does not support additionalDirectories", n, r);
	if ((e.additionalDirectories?.length ?? 0) > 64) throw $("ACP additionalDirectories is limited to 64 entries", n, r);
	if ((e.mcpServers?.length ?? 0) > 32) throw $("ACP MCP configuration is limited to 32 servers", n, r);
	for (let i of e.mcpServers ?? []) Wf(i, t, n, r);
}
function Vf(e, t, n) {
	if (e.length > 256) throw $("ACP prompts are limited to 256 content blocks", n, "prompt");
	for (let r of e) if (Uf(r, n), r.type !== "text" && r.type !== "resource_link" && !(r.type === "image" && t.image) && !(r.type === "audio" && t.audio) && !(r.type === "resource" && t.embeddedContext)) throw $(`The agent does not support prompt content type '${r.type}'`, n, "prompt");
}
async function Hf(t, n, r) {
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
function Uf(e, t) {
	if (e.type === "text" && typeof e.text == "string" && e.text.length > 1048576) throw $("ACP text content is limited to 1 MiB", t, "prompt");
	if ((e.type === "image" || e.type === "audio") && typeof e.data == "string" && e.data.length > 8388608) throw $("ACP media content is limited to 8 MiB of base64 data", t, "prompt");
	if (e.type === "resource" && typeof e.resource == "object" && e.resource !== null) {
		let n = e.resource;
		if (typeof n.text == "string" && n.text.length > 1048576) throw $("ACP embedded resource text is limited to 1 MiB", t, "prompt");
		if (typeof n.blob == "string" && n.blob.length > 8388608) throw $("ACP embedded resource data is limited to 8 MiB", t, "prompt");
	}
}
function Wf(e, t, n, r) {
	if (e.type === "sse" && n !== 1) throw $("SSE MCP servers are available only with protocol: 1", n, r);
	if (!t.mcp[e.type]) throw $(`The agent does not support ${e.type} MCP servers`, n, r);
}
function $(t, n, r) {
	return new e("INVALID_CONFIGURATION", t, {
		...n === void 0 ? {} : { protocol: n },
		phase: r
	});
}
function Gf(e) {
	return e.startsWith("/") || /^[A-Za-z]:[\\/]/.test(e) || e.startsWith("\\\\");
}
//#endregion
export { F as A, P as B, Bu as C, To as D, wo as E, j as F, f as G, Yi as H, I, e as K, z as L, M, R as N, H as O, B as P, k as R, Hu as S, V as T, m as U, Sa as V, d as W, fd as _, Lf as a, ad as b, _f as c, Z as d, df as f, qd as g, hf as h, zf as i, N as j, U as k, Q as l, mf as m, Vf as n, If as o, pf as p, t as q, Bf as r, Rf as s, Hf as t, uf as u, sd as v, ld as w, K as x, G as y, L as z };

//# sourceMappingURL=types.js.map