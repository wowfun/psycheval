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
//#region src/core/protocol/normalize.ts
var ae = 1e3, oe = 64, se = 256, m = 16384, ce = 256, le = 1048576, ue = 8388608, de = 1048576, fe = 4096, pe = 4194304, me = 4096, he = 16;
function h(e) {
	return typeof e == "object" && !!e && !Array.isArray(e);
}
function g(e, t = m) {
	return typeof e == "string" ? ze(e, t) : void 0;
}
function ge(e) {
	let t = g(e, m);
	if (t) try {
		let e = new URL(t).protocol;
		return e === "http:" || e === "https:" ? t : void 0;
	} catch {
		return;
	}
}
function _(e, t = se) {
	return Array.isArray(e) ? e.slice(0, t).filter(h) : [];
}
function _e(e) {
	return Array.isArray(e) ? e.slice(0, ce).flatMap((e) => {
		let t = Me(e);
		return t ? [t] : [];
	}) : [];
}
function ve(e) {
	let t = Le(e, { nodes: me }, 0);
	return h(t) ? t : void 0;
}
function ye(e) {
	return _(e).map((e, t) => ({
		id: g(e.methodId) ?? g(e.id) ?? `auth-${t}`,
		name: g(e.name) ?? g(e.title) ?? `Authentication ${t + 1}`,
		...g(e.description) ? { description: g(e.description) } : {},
		type: g(e.type) ?? "agent",
		raw: ve(e) ?? {}
	}));
}
function be(e) {
	return _(e).flatMap((e) => {
		let t = g(e.name);
		if (!t) return [];
		let n = h(e.input) ? e.input : void 0;
		return [{
			name: t,
			description: g(e.description) ?? "",
			...n && g(n.hint) ? { inputHint: g(n.hint) } : {}
		}];
	});
}
function xe(e) {
	return _(e).flatMap((e) => {
		let t = g(e.configId) ?? g(e.id);
		if (!t) return [];
		let n = g(e.type), r = e.currentValue, i = n === "boolean" || typeof r == "boolean" ? "boolean" : n === "select" || Array.isArray(e.options) ? "select" : "unknown", a = typeof r == "boolean" ? r : g(r) ?? "", o = [], s = (e, t) => {
			let n = g(e.value);
			if (!n) return;
			let r = g(e.description);
			o.push({
				value: n,
				name: g(e.name) ?? n,
				...t ? { group: t } : {},
				...r ? { description: r } : {}
			});
		}, c = se;
		for (let t of _(e.options)) {
			if (!c) break;
			if (Array.isArray(t.options)) {
				let e = g(t.name) ?? g(t.group), n = Math.min(t.options.length, c);
				for (let r of _(t.options, n)) s(r, e);
				c -= n;
			} else s(t), c--;
		}
		return [{
			id: t,
			name: g(e.name) ?? t,
			...g(e.description) ? { description: g(e.description) } : {},
			...g(e.category) ? { category: g(e.category) } : {},
			type: i,
			currentValue: a,
			...o.length ? { options: o } : {}
		}];
	});
}
function Se(e) {
	if (!h(e)) return [];
	let t = _(e.availableModes), n = g(e.currentModeId) ?? "";
	return t.length ? [{
		id: "mode",
		name: "Mode",
		category: "mode",
		type: "select",
		currentValue: n,
		options: t.flatMap((e) => {
			let t = g(e.id);
			return t ? [{
				value: t,
				name: g(e.name) ?? t,
				...g(e.description) ? { description: g(e.description) } : {}
			}] : [];
		})
	}] : [];
}
function Ce(e) {
	if (!h(e)) return { sessions: [] };
	let t = _(e.sessions).flatMap((e) => {
		let t = g(e.sessionId);
		return t ? [{
			sessionId: t,
			...g(e.title) ? { title: g(e.title) } : {},
			...g(e.updatedAt) ? { updatedAt: g(e.updatedAt) } : {},
			...g(e.cwd) ? { cwd: g(e.cwd) } : {}
		}] : [];
	}), n = g(e.nextCursor);
	return {
		sessions: t,
		...n ? { nextCursor: n } : {}
	};
}
function we(e) {
	if (!h(e) || !He(e.used) || !He(e.size)) return;
	let t = h(e.cost) ? g(e.cost.currency) : void 0, n = h(e.cost) && He(e.cost.amount) && t !== void 0 ? {
		amount: e.cost.amount,
		currency: t
	} : void 0;
	return {
		used: e.used,
		size: e.size,
		...n ? { cost: n } : {}
	};
}
var Te = class {
	#e = [];
	#t = 0;
	#n = /* @__PURE__ */ new Map();
	#r = 0;
	#i = /* @__PURE__ */ new WeakMap();
	get imageRevision() {
		return this.#r;
	}
	#a(e) {
		let t = We(e, this.#i);
		t !== (this.#n.get(e.id) ?? 0) && (t ? this.#n.set(e.id, t) : this.#n.delete(e.id), this.#r++);
	}
	#o(e) {
		this.#n.delete(e) && this.#r++;
	}
	#s = /* @__PURE__ */ new Map();
	#c;
	#l;
	#u = /* @__PURE__ */ new Set();
	#d = /* @__PURE__ */ new Set();
	#f;
	#p = /* @__PURE__ */ new Map();
	get activities() {
		return this.#e;
	}
	imagePayloads() {
		return [...this.#n].map(([e, t]) => ({
			activityId: e,
			bytes: t,
			protected: e === this.#c
		}));
	}
	evictImages(e) {
		this.#S(e, (e) => Ge(e));
	}
	reset() {
		this.#n.clear(), this.#i = /* @__PURE__ */ new WeakMap(), this.#r++, this.#e = [], this.#s.clear(), this.#c = void 0, this.#l = void 0, this.#u.clear(), this.#d.clear(), this.#f = void 0, this.#p.clear();
	}
	beginTurn() {
		this.#s.clear(), this.#l = void 0;
	}
	addNotice(e) {
		let t = this.#e.filter((e) => e.type === "notice").length - oe + 1;
		t > 0 && (this.#e = this.#e.filter((e) => e.type !== "notice" || t <= 0 || (--t, !1))), this.#D(e);
	}
	addUserMessage(e, t, n) {
		let r = Ee(n), i = _e(e), a = `local-user-${++this.#t}`;
		return this.#D({
			type: "message",
			id: a,
			role: "user",
			content: i,
			...r === void 0 ? {} : { timestamp: r },
			...t ? { pending: !0 } : {}
		}), this.#l = r, (this.#n.has(a) || this.#c && this.#n.has(this.#c)) && this.#r++, this.#c = t ? a : void 0, a;
	}
	markFinalAnswer(e, t) {
		let n = Ee(e);
		if (n !== void 0 || t !== void 0) for (let e = this.#e.length - 1; e >= 0; --e) {
			let r = this.#e[e];
			if (r?.type === "message") {
				if (r.role === "user") return;
				if (r.role === "assistant") {
					this.#S(r.id, () => ({
						...r,
						...n === void 0 ? {} : { timestamp: Math.max(n, this.#l ?? n) },
						...t === void 0 ? {} : { replayCompleted: t }
					}));
					return;
				}
			}
		}
	}
	finishTurn(e) {
		this.#c && this.#n.has(this.#c) && this.#r++, e !== void 0 && this.markFinalAnswer(e), this.#c && this.#S(this.#c, (e) => {
			if (e.type !== "message") return e;
			let { pending: t, ...n } = e;
			return n;
		}), this.#c = void 0;
	}
	finalizeReplay() {
		this.#w();
		let e = [];
		for (let t of this.#e) t.type !== "message" || t.role !== "user" || this.#d.has(t.id) || p(t.content).status === "malformed" && (this.#d.add(t.id), e.push({
			code: "MALFORMED_USER_MESSAGE_ENVELOPE",
			message: "A restored user-message envelope was incomplete; retained the Agent history unchanged"
		}));
		return e.length ? { diagnostics: e } : {};
	}
	markUserAccepted(e = []) {
		if (this.#c) {
			this.#S(this.#c, (e) => e.type === "message" ? {
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
				this.#D(e);
			}
		}
	}
	reduce(e, t) {
		if (!h(e) || typeof e.sessionUpdate != "string") return { unsupported: "invalid_update" };
		let n = g(e.sessionUpdate) ?? "";
		if (this.#c && (n === "user_message_chunk" || n === "user_message")) return {};
		switch (n) {
			case "user_message_chunk":
			case "agent_message_chunk":
			case "agent_thought_chunk": {
				let r = n === "user_message_chunk" ? "user" : n === "agent_message_chunk" ? "assistant" : "thought";
				return this.#m(r, g(e.messageId), e.content, t), {};
			}
			case "user_message":
			case "agent_message":
			case "agent_thought": {
				let t = n === "user_message" ? "user" : n === "agent_message" ? "assistant" : "thought";
				return this.#h(t, g(e.messageId), e), {};
			}
			case "tool_call":
			case "tool_call_update": return this.#g(e), {};
			case "tool_call_content_chunk": return this.#_(e), {};
			case "plan":
			case "plan_update": return this.#v(e), {};
			case "plan_removed": return this.#C(`plan:${g(e.planId) ?? "primary"}`), {};
			case "terminal_update": return this.#y(e), {};
			case "terminal_output_chunk": return this.#b(e), {};
			case "available_commands_update": return { commands: be(e.availableCommands) };
			case "config_option_update": return { configOptions: xe(e.configOptions) };
			case "current_mode_update": return {};
			case "session_info_update": return { sessionTitle: Object.hasOwn(e, "title") ? g(e.title) ?? null : void 0 };
			case "usage_update": return { usage: we(e) };
			case "state_update": {
				let t = g(e.state);
				return t === "running" || t === "requires_action" || t === "idle" ? {
					state: t,
					...g(e.stopReason) ? { stopReason: g(e.stopReason) } : {}
				} : { unsupported: `state:${t ?? "missing"}` };
			}
			default: return { unsupported: n };
		}
	}
	#m(e, t, n, r) {
		let i = t;
		if (!i && r === 1 && (i = this.#s.get(e) ?? `v1-${e}-${++this.#t}`, this.#s.set(e, i)), !i) return;
		let a = De(e, i);
		if (this.#f && (e !== "user" || this.#f !== a) && this.#w(), e === "user" && this.#u.has(a)) return;
		let o = this.#e.find((e) => e.type === "message" && e.id === a), s = Me(n);
		s && (o?.type === "message" ? this.#S(a, () => ({
			...o,
			content: Ae(o.content, s)
		})) : this.#D({
			type: "message",
			id: a,
			role: e,
			content: [s]
		}), e === "user" && (this.#f = a));
	}
	#h(e, t, n) {
		if (!t) return;
		this.#w();
		let r = De(e, t), i = this.#e.find((e) => e.type === "message" && e.id === r), a = Object.hasOwn(n, "content") ? _e(n.content) : i?.type === "message" ? i.content : [], o = e === "user" ? p(a) : void 0, s = o?.status === "restored" ? o.content : a;
		i?.type === "message" ? this.#S(r, () => ({
			...i,
			role: e,
			content: s
		})) : this.#D({
			type: "message",
			id: r,
			role: e,
			content: s
		}), o?.status === "restored" && this.#T(r, o);
	}
	#g(e) {
		let t = g(e.toolCallId);
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
			...Object.hasOwn(e, "title") ? { title: g(e.title) ?? "Tool" } : {},
			...Object.hasOwn(e, "kind") && g(e.kind) ? { kind: g(e.kind) } : {},
			...Object.hasOwn(e, "status") ? { status: g(e.status) ?? "pending" } : {},
			...Object.hasOwn(e, "content") ? { content: Pe(e.content) } : {},
			...Object.hasOwn(e, "locations") ? { locations: Pe(e.locations).filter(h) } : {},
			...Object.hasOwn(e, "rawInput") ? { rawInput: Fe(e.rawInput) } : {},
			...Object.hasOwn(e, "rawOutput") ? { rawOutput: Fe(e.rawOutput) } : {}
		}, s = Oe(o), c = {
			...o,
			...s ? { subagent: s } : {}
		};
		this.#x(n, c);
	}
	#_(e) {
		let t = g(e.toolCallId);
		if (!t || !Object.hasOwn(e, "content")) return;
		let n = `tool:${t}`, r = this.#e.find((e) => e.type === "tool" && e.id === n), i = r?.type === "tool" ? r : {
			type: "tool",
			id: n,
			title: "Tool",
			status: "pending",
			content: [],
			locations: []
		};
		i.content.length >= se || this.#x(n, {
			...i,
			content: Pe([...i.content, e.content])
		});
	}
	#v(e) {
		let t = h(e.plan) ? e.plan : e, n = `plan:${g(t.planId) ?? "primary"}`, r = {
			type: "plan",
			id: n,
			entries: _(t.entries).map((e) => ({
				content: g(e.content) ?? "",
				...g(e.priority) ? { priority: g(e.priority) } : {},
				status: g(e.status) ?? "pending"
			}))
		};
		this.#x(n, r);
	}
	#y(e) {
		let t = g(e.terminalId);
		if (!t) return;
		let n = `terminal:${t}`;
		if (Object.hasOwn(e, "output") && h(e.output) && typeof e.output.data == "string") {
			let n = new TextDecoder(), r = je(e.output.data).subarray(0, pe), i = Re(n.decode(r, { stream: !0 }), de);
			this.#p.set(t, {
				decoder: n,
				output: i,
				chunks: 1,
				decodedBytes: r.byteLength
			});
		}
		let r = this.#e.find((e) => e.type === "terminal" && e.id === n), i = Array.isArray(e.command) ? e.command.filter((e) => typeof e == "string").join(" ") : g(e.command), a = this.#p.get(t)?.output ?? "", o = {
			type: "terminal",
			id: n,
			title: i ?? (r?.type === "terminal" ? r.title : "Terminal"),
			output: a,
			exited: Object.hasOwn(e, "exitStatus") ? e.exitStatus !== null : r?.type === "terminal" && r.exited
		};
		this.#x(n, o);
	}
	#b(e) {
		let t = g(e.terminalId), n = g(e.data);
		if (!t || !n) return;
		let r = this.#p.get(t) ?? {
			decoder: new TextDecoder(),
			output: "",
			chunks: 0,
			decodedBytes: 0
		};
		if (r.chunks >= fe || r.decodedBytes >= pe) return;
		let i = pe - r.decodedBytes, a = je(n).subarray(0, i);
		r.chunks += 1, r.decodedBytes += a.byteLength, r.output = Re(r.output + r.decoder.decode(a, { stream: !0 }), de), this.#p.set(t, r);
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
		this.#x(o, c);
	}
	#x(e, t) {
		let n = this.#e.findIndex((t) => t.id === e);
		if (n < 0) {
			this.#D(t);
			return;
		}
		this.#a(t), this.#e = this.#e.map((e, r) => r === n ? t : e);
	}
	#S(e, t) {
		this.#e = this.#e.map((n) => {
			if (n.id !== e) return n;
			let r = t(n);
			return this.#a(r), r;
		});
	}
	#C(e) {
		this.#o(e), this.#e = this.#e.filter((t) => t.id !== e);
	}
	#w() {
		let e = this.#f;
		if (this.#f = void 0, !e || this.#u.has(e)) return;
		let t = this.#e.find((t) => t.id === e);
		if (t?.type !== "message" || t.role !== "user") return;
		let n = p(t.content);
		n.status === "restored" && this.#T(e, n);
	}
	#T(e, t) {
		this.#u.has(e) || (this.#u.add(e), this.#S(e, (e) => e.type === "message" ? {
			...e,
			content: t.content
		} : e), this.#E(e, t.context.map((e) => ({
			type: "context",
			id: `restored-context-${++this.#t}`,
			contextId: e.id,
			label: e.label,
			content: e.content
		}))));
	}
	#E(e, t) {
		if (!t.length) return;
		let n = this.#e.findIndex((t) => t.id === e);
		n < 0 || (t.forEach((e) => this.#a(e)), this.#e = [
			...this.#e.slice(0, n + 1),
			...t,
			...this.#e.slice(n + 1)
		], this.#O());
	}
	#D(e) {
		this.#a(e), this.#e = [...this.#e, e], this.#O();
	}
	#O() {
		let e = this.#e.filter((e) => e.type !== "notice").length - ae;
		if (e <= 0) return;
		let t = [];
		this.#e = this.#e.filter((n) => n.type === "notice" || n.id === this.#c || e <= 0 || (--e, t.push(n), !1));
		for (let e of t) this.#o(e.id), e.type === "terminal" && this.#p.delete(e.id.slice(9));
	}
};
function Ee(e) {
	if (!(e === void 0 || !Number.isFinite(e) || e < 0 || Number.isNaN(new Date(e).valueOf()))) return e;
}
function De(e, t) {
	return `message:${e}:${t}`;
}
function Oe(e) {
	if (e.kind !== "think" || !h(e.rawInput)) return;
	let t = g(e.rawInput.subagent_type), n = g(e.rawInput.description), r = g(e.rawInput.prompt);
	if (!t || !n || !r) return;
	let i = h(e.rawOutput) && h(e.rawOutput.metadata) ? e.rawOutput.metadata : void 0, a = ke(i?.sessionId), o = ke(e.rawInput.task_id), s = a ?? o, c = e.rawInput.background === !0 || i?.background === !0;
	return {
		agent: t,
		...n ? { description: n } : {},
		...s ? { sessionId: s } : {},
		background: c
	};
}
function ke(e) {
	return typeof e == "string" && e.length > 0 && e.length <= m ? e : void 0;
}
function Ae(e, t) {
	let n = e.at(-1);
	return n?.type === "text" && typeof n.text == "string" && t.type === "text" && typeof t.text == "string" && n.annotations == null && n._meta == null && t.annotations == null && t._meta == null ? [...e.slice(0, -1), {
		type: "text",
		text: Re(n.text + t.text, le)
	}] : e.length >= ce ? [...e] : [...e, t];
}
function je(e) {
	try {
		if (typeof globalThis.atob == "function") {
			let t = globalThis.atob(e.slice(0, ue));
			return Uint8Array.from(t, (e) => e.charCodeAt(0));
		}
		return new Uint8Array(Buffer.from(e.slice(0, ue), "base64"));
	} catch {
		return /* @__PURE__ */ new Uint8Array();
	}
}
function Me(e) {
	if (!h(e)) return;
	let t = g(e.type, 128);
	if (!t) return;
	let n = Ne(e._meta), r = {
		type: t,
		...n
	};
	if (t === "text") {
		let t = g(e.text, le);
		return t === void 0 ? void 0 : {
			...r,
			type: "text",
			text: t
		};
	}
	if (t === "image" || t === "audio") {
		let n = g(e.data, ue), i = g(e.mimeType, 256);
		return n === void 0 || i === void 0 ? void 0 : {
			...r,
			type: t,
			data: n,
			mimeType: i
		};
	}
	if (t === "resource_link") {
		let t = n ? g(e.uri, m) : Ue(e.uri), i = g(e.name, m);
		return !t || !i ? void 0 : {
			...r,
			type: "resource_link",
			uri: t,
			name: i,
			...g(e.title) ? { title: g(e.title) } : {},
			...g(e.description) ? { description: g(e.description) } : {},
			...g(e.mimeType, 256) ? { mimeType: g(e.mimeType, 256) } : {},
			...typeof e.size == "number" && Number.isFinite(e.size) ? { size: e.size } : {}
		};
	}
	if (t === "resource" && h(e.resource)) {
		let t = n ? g(e.resource.uri, m) : Ue(e.resource.uri);
		return t ? {
			...r,
			type: "resource",
			resource: {
				uri: t,
				...g(e.resource.mimeType, 256) ? { mimeType: g(e.resource.mimeType, 256) } : {},
				...g(e.resource.text, 1048576) === void 0 ? {} : { text: g(e.resource.text, le) },
				...g(e.resource.blob, 8388608) === void 0 ? {} : { blob: g(e.resource.blob, ue) }
			}
		} : void 0;
	}
	return r;
}
function Ne(e) {
	if (!h(e)) return;
	let t = e["pretty-aui/context"];
	if (!(!h(t) || t.version !== 1 || typeof t.id != "string" || !t.id.trim() || t.id.length > m || typeof t.label != "string" || !t.label.trim() || t.label.length > m)) return { _meta: { "pretty-aui/context": {
		version: 1,
		id: t.id,
		label: t.label
	} } };
}
function Pe(e) {
	if (!Array.isArray(e)) return [];
	let t = Le(e, { nodes: me }, 0);
	return Array.isArray(t) ? t : [];
}
function Fe(e) {
	let t = Le(e, { nodes: me }, 0);
	return t === Ie ? null : t;
}
var Ie = Symbol("omit-structured-value");
function Le(e, t, n) {
	if (t.nodes <= 0 || n > he) return Ie;
	if (--t.nodes, typeof e == "string") return ze(e, le);
	if (e === null || typeof e == "boolean" || typeof e == "number" && Number.isFinite(e)) return e;
	if (Array.isArray(e)) {
		let r = [];
		for (let i of e.slice(0, se)) {
			let e = Le(i, t, n + 1);
			if (e !== Ie && r.push(e), t.nodes <= 0) break;
		}
		return r;
	}
	if (h(e)) {
		let r = {};
		for (let [i, a] of Object.entries(e).slice(0, se)) {
			let e = Le(a, t, n + 1);
			if (e !== Ie && (r[ze(i, m)] = e), t.nodes <= 0) break;
		}
		return r;
	}
	return null;
}
function Re(e, t) {
	if (e.length <= t) return e;
	let n = e.length - t;
	return Ve(e.charCodeAt(n)) && (n += 1), e.slice(n);
}
function ze(e, t) {
	if (e.length <= t) return e;
	let n = t;
	return Be(e.charCodeAt(n - 1)) && --n, e.slice(0, n);
}
function Be(e) {
	return e >= 55296 && e <= 56319;
}
function Ve(e) {
	return e >= 56320 && e <= 57343;
}
function He(e) {
	return typeof e == "number" && Number.isFinite(e) && e >= 0 && !Object.is(e, -0);
}
function Ue(e) {
	let t = g(e, m);
	if (t) try {
		let e = new URL(t).protocol;
		return e === "http:" || e === "https:" || e === "file:" ? t : void 0;
	} catch {
		return;
	}
}
function We(e, t) {
	if (!Array.isArray(e) && !h(e)) return 0;
	let n = t.get(e);
	if (n !== void 0) return n;
	let r = !Array.isArray(e) && e.type === "image" && typeof e.data == "string" ? e.data.length : Object.values(e).reduce((e, n) => e + We(n, t), 0);
	return t.set(e, r), r;
}
function Ge(e) {
	return Array.isArray(e) ? e.map(Ge) : h(e) ? e.type === "image" && typeof e.data == "string" ? {
		type: "image_unavailable",
		mimeType: e.mimeType
	} : Object.fromEntries(Object.entries(e).map(([e, t]) => [e, Ge(t)])) : e;
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/schema/index.js
var v = {
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
}, y = {
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
}, Ke = { cancel_request: "$/cancel_request" }, qe, Je = /*@__PURE__*/ Object.freeze({ status: "aborted" });
function b(e, t, n) {
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
var Ye = class extends Error {
	constructor() {
		super("Encountered Promise during synchronous parse. Use .parseAsync() instead.");
	}
}, Xe = class extends Error {
	constructor(e) {
		super(`Encountered unidirectional transform during encode: ${e}`), this.name = "ZodEncodeError";
	}
};
(qe = globalThis).__zod_globalConfig ?? (qe.__zod_globalConfig = {});
var Ze = globalThis.__zod_globalConfig;
function x(e) {
	return e && Object.assign(Ze, e), Ze;
}
//#endregion
//#region node_modules/.pnpm/zod@4.4.3/node_modules/zod/v4/core/util.js
function Qe(e) {
	let t = Object.values(e).filter((e) => typeof e == "number");
	return Object.entries(e).filter(([e, n]) => t.indexOf(+e) === -1).map(([e, t]) => t);
}
function $e(e, t) {
	return typeof t == "bigint" ? t.toString() : t;
}
function et(e) {
	return { get value() {
		{
			let t = e();
			return Object.defineProperty(this, "value", { value: t }), t;
		}
	} };
}
function tt(e) {
	return e == null;
}
function nt(e) {
	let t = +!!e.startsWith("^"), n = e.endsWith("$") ? e.length - 1 : e.length;
	return e.slice(t, n);
}
function rt(e, t) {
	let n = e / t, r = Math.round(n), i = 2 ** -52 * Math.max(Math.abs(n), 1);
	return Math.abs(n - r) < i ? 0 : n - r;
}
var it = /* @__PURE__*/ Symbol("evaluating");
function S(e, t, n) {
	let r;
	Object.defineProperty(e, t, {
		get() {
			if (r !== it) return r === void 0 && (r = it, r = n()), r;
		},
		set(n) {
			Object.defineProperty(e, t, { value: n });
		},
		configurable: !0
	});
}
function at(e, t, n) {
	Object.defineProperty(e, t, {
		value: n,
		writable: !0,
		enumerable: !0,
		configurable: !0
	});
}
function ot(...e) {
	let t = {};
	for (let n of e) {
		let e = Object.getOwnPropertyDescriptors(n);
		Object.assign(t, e);
	}
	return Object.defineProperties({}, t);
}
function st(e) {
	return JSON.stringify(e);
}
function ct(e) {
	return e.toLowerCase().trim().replace(/[^\w\s-]/g, "").replace(/[\s_-]+/g, "-").replace(/^-+|-+$/g, "");
}
var lt = "captureStackTrace" in Error ? Error.captureStackTrace : (...e) => {};
function ut(e) {
	return typeof e == "object" && !!e && !Array.isArray(e);
}
var dt = /* @__PURE__*/ et(() => {
	if (Ze.jitless || typeof navigator < "u" && navigator?.userAgent?.includes("Cloudflare")) return !1;
	try {
		return Function(""), !0;
	} catch {
		return !1;
	}
});
function ft(e) {
	if (ut(e) === !1) return !1;
	let t = e.constructor;
	if (t === void 0 || typeof t != "function") return !0;
	let n = t.prototype;
	return ut(n) !== !1 && Object.prototype.hasOwnProperty.call(n, "isPrototypeOf") !== !1;
}
function pt(e) {
	return ft(e) ? { ...e } : Array.isArray(e) ? [...e] : e instanceof Map ? new Map(e) : e instanceof Set ? new Set(e) : e;
}
var mt = /* @__PURE__*/ new Set([
	"string",
	"number",
	"symbol"
]);
function ht(e) {
	return e.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
function gt(e, t, n) {
	let r = new e._zod.constr(t ?? e._zod.def);
	return (!t || n?.parent) && (r._zod.parent = e), r;
}
function C(e) {
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
function _t(e) {
	return Object.keys(e).filter((t) => e[t]._zod.optin === "optional" && e[t]._zod.optout === "optional");
}
var vt = {
	safeint: [-(2 ** 53 - 1), 2 ** 53 - 1],
	int32: [-2147483648, 2147483647],
	uint32: [0, 4294967295],
	float32: [-34028234663852886e22, 34028234663852886e22],
	float64: [-Number.MAX_VALUE, Number.MAX_VALUE]
};
function yt(e, t) {
	let n = e._zod.def, r = n.checks;
	if (r && r.length > 0) throw Error(".pick() cannot be used on object schemas containing refinements");
	return gt(e, ot(e._zod.def, {
		get shape() {
			let e = {};
			for (let r in t) {
				if (!(r in n.shape)) throw Error(`Unrecognized key: "${r}"`);
				t[r] && (e[r] = n.shape[r]);
			}
			return at(this, "shape", e), e;
		},
		checks: []
	}));
}
function bt(e, t) {
	let n = e._zod.def, r = n.checks;
	if (r && r.length > 0) throw Error(".omit() cannot be used on object schemas containing refinements");
	return gt(e, ot(e._zod.def, {
		get shape() {
			let r = { ...e._zod.def.shape };
			for (let e in t) {
				if (!(e in n.shape)) throw Error(`Unrecognized key: "${e}"`);
				t[e] && delete r[e];
			}
			return at(this, "shape", r), r;
		},
		checks: []
	}));
}
function xt(e, t) {
	if (!ft(t)) throw Error("Invalid input to extend: expected a plain object");
	let n = e._zod.def.checks;
	if (n && n.length > 0) {
		let n = e._zod.def.shape;
		for (let e in t) if (Object.getOwnPropertyDescriptor(n, e) !== void 0) throw Error("Cannot overwrite keys on object schemas containing refinements. Use `.safeExtend()` instead.");
	}
	return gt(e, ot(e._zod.def, { get shape() {
		let n = {
			...e._zod.def.shape,
			...t
		};
		return at(this, "shape", n), n;
	} }));
}
function St(e, t) {
	if (!ft(t)) throw Error("Invalid input to safeExtend: expected a plain object");
	return gt(e, ot(e._zod.def, { get shape() {
		let n = {
			...e._zod.def.shape,
			...t
		};
		return at(this, "shape", n), n;
	} }));
}
function Ct(e, t) {
	if (e._zod.def.checks?.length) throw Error(".merge() cannot be used on object schemas containing refinements. Use .safeExtend() instead.");
	return gt(e, ot(e._zod.def, {
		get shape() {
			let n = {
				...e._zod.def.shape,
				...t._zod.def.shape
			};
			return at(this, "shape", n), n;
		},
		get catchall() {
			return t._zod.def.catchall;
		},
		checks: t._zod.def.checks ?? []
	}));
}
function wt(e, t, n) {
	let r = t._zod.def.checks;
	if (r && r.length > 0) throw Error(".partial() cannot be used on object schemas containing refinements");
	return gt(t, ot(t._zod.def, {
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
			return at(this, "shape", i), i;
		},
		checks: []
	}));
}
function Tt(e, t, n) {
	return gt(t, ot(t._zod.def, { get shape() {
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
		return at(this, "shape", i), i;
	} }));
}
function Et(e, t = 0) {
	if (e.aborted === !0) return !0;
	for (let n = t; n < e.issues.length; n++) if (e.issues[n]?.continue !== !0) return !0;
	return !1;
}
function Dt(e, t = 0) {
	if (e.aborted === !0) return !0;
	for (let n = t; n < e.issues.length; n++) if (e.issues[n]?.continue === !1) return !0;
	return !1;
}
function Ot(e, t) {
	return t.map((t) => {
		var n;
		return (n = t).path ?? (n.path = []), t.path.unshift(e), t;
	});
}
function kt(e) {
	return typeof e == "string" ? e : e?.message;
}
function w(e, t, n) {
	let r = e.message ? e.message : kt(e.inst?._zod.def?.error?.(e)) ?? kt(t?.error?.(e)) ?? kt(n.customError?.(e)) ?? kt(n.localeError?.(e)) ?? "Invalid input", { inst: i, continue: a, input: o, ...s } = e;
	return s.path ??= [], s.message = r, t?.reportInput && (s.input = o), s;
}
function At(e) {
	return Array.isArray(e) ? "array" : typeof e == "string" ? "string" : "unknown";
}
function jt(...e) {
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
var Mt = (e, t) => {
	e.name = "$ZodError", Object.defineProperty(e, "_zod", {
		value: e._zod,
		enumerable: !1
	}), Object.defineProperty(e, "issues", {
		value: t,
		enumerable: !1
	}), e.message = JSON.stringify(t, $e, 2), Object.defineProperty(e, "toString", {
		value: () => e.message,
		enumerable: !1
	});
}, Nt = b("$ZodError", Mt), Pt = b("$ZodError", Mt, { Parent: Error });
function Ft(e, t = (e) => e.message) {
	let n = {}, r = [];
	for (let i of e.issues) i.path.length > 0 ? (n[i.path[0]] = n[i.path[0]] || [], n[i.path[0]].push(t(i))) : r.push(t(i));
	return {
		formErrors: r,
		fieldErrors: n
	};
}
function It(e, t = (e) => e.message) {
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
var Lt = (e) => (t, n, r, i) => {
	let a = r ? {
		...r,
		async: !1
	} : { async: !1 }, o = t._zod.run({
		value: n,
		issues: []
	}, a);
	if (o instanceof Promise) throw new Ye();
	if (o.issues.length) {
		let t = new ((i?.Err) ?? e)(o.issues.map((e) => w(e, a, x())));
		throw lt(t, i?.callee), t;
	}
	return o.value;
}, Rt = (e) => async (t, n, r, i) => {
	let a = r ? {
		...r,
		async: !0
	} : { async: !0 }, o = t._zod.run({
		value: n,
		issues: []
	}, a);
	if (o instanceof Promise && (o = await o), o.issues.length) {
		let t = new ((i?.Err) ?? e)(o.issues.map((e) => w(e, a, x())));
		throw lt(t, i?.callee), t;
	}
	return o.value;
}, zt = (e) => (t, n, r) => {
	let i = r ? {
		...r,
		async: !1
	} : { async: !1 }, a = t._zod.run({
		value: n,
		issues: []
	}, i);
	if (a instanceof Promise) throw new Ye();
	return a.issues.length ? {
		success: !1,
		error: new (e ?? Nt)(a.issues.map((e) => w(e, i, x())))
	} : {
		success: !0,
		data: a.value
	};
}, Bt = /* @__PURE__*/ zt(Pt), Vt = (e) => async (t, n, r) => {
	let i = r ? {
		...r,
		async: !0
	} : { async: !0 }, a = t._zod.run({
		value: n,
		issues: []
	}, i);
	return a instanceof Promise && (a = await a), a.issues.length ? {
		success: !1,
		error: new e(a.issues.map((e) => w(e, i, x())))
	} : {
		success: !0,
		data: a.value
	};
}, Ht = /* @__PURE__*/ Vt(Pt), Ut = (e) => (t, n, r) => {
	let i = r ? {
		...r,
		direction: "backward"
	} : { direction: "backward" };
	return Lt(e)(t, n, i);
}, Wt = (e) => (t, n, r) => Lt(e)(t, n, r), Gt = (e) => async (t, n, r) => {
	let i = r ? {
		...r,
		direction: "backward"
	} : { direction: "backward" };
	return Rt(e)(t, n, i);
}, Kt = (e) => async (t, n, r) => Rt(e)(t, n, r), qt = (e) => (t, n, r) => {
	let i = r ? {
		...r,
		direction: "backward"
	} : { direction: "backward" };
	return zt(e)(t, n, i);
}, Jt = (e) => (t, n, r) => zt(e)(t, n, r), Yt = (e) => async (t, n, r) => {
	let i = r ? {
		...r,
		direction: "backward"
	} : { direction: "backward" };
	return Vt(e)(t, n, i);
}, Xt = (e) => async (t, n, r) => Vt(e)(t, n, r), Zt = /^[cC][0-9a-z]{6,}$/, Qt = /^[0-9a-z]+$/, $t = /^[0-9A-HJKMNP-TV-Za-hjkmnp-tv-z]{26}$/, en = /^[0-9a-vA-V]{20}$/, tn = /^[A-Za-z0-9]{27}$/, nn = /^[a-zA-Z0-9_-]{21}$/, rn = /^P(?:(\d+W)|(?!.*W)(?=\d|T\d)(\d+Y)?(\d+M)?(\d+D)?(T(?=\d)(\d+H)?(\d+M)?(\d+([.,]\d+)?S)?)?)$/, an = /^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$/, on = (e) => e ? RegExp(`^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-${e}[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12})$`) : /^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$/, sn = /^(?!\.)(?!.*\.\.)([A-Za-z0-9_'+\-\.]*)[A-Za-z0-9_+-]@([A-Za-z0-9][A-Za-z0-9\-]*\.)+[A-Za-z]{2,}$/, cn = "^(\\p{Extended_Pictographic}|\\p{Emoji_Component})+$";
function ln() {
	return new RegExp(cn, "u");
}
var un = /^(?:(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])\.){3}(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])$/, dn = /^(([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:))$/, fn = /^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])\/([0-9]|[1-2][0-9]|3[0-2])$/, pn = /^(([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|::|([0-9a-fA-F]{1,4})?::([0-9a-fA-F]{1,4}:?){0,6})\/(12[0-8]|1[01][0-9]|[1-9]?[0-9])$/, mn = /^$|^(?:[0-9a-zA-Z+/]{4})*(?:(?:[0-9a-zA-Z+/]{2}==)|(?:[0-9a-zA-Z+/]{3}=))?$/, hn = /^[A-Za-z0-9_-]*$/, gn = /^https?$/, _n = /^\+[1-9]\d{6,14}$/, vn = "(?:(?:\\d\\d[2468][048]|\\d\\d[13579][26]|\\d\\d0[48]|[02468][048]00|[13579][26]00)-02-29|\\d{4}-(?:(?:0[13578]|1[02])-(?:0[1-9]|[12]\\d|3[01])|(?:0[469]|11)-(?:0[1-9]|[12]\\d|30)|(?:02)-(?:0[1-9]|1\\d|2[0-8])))", yn = /*@__PURE__*/ RegExp(`^${vn}$`);
function bn(e) {
	let t = "(?:[01]\\d|2[0-3]):[0-5]\\d";
	return typeof e.precision == "number" ? e.precision === -1 ? `${t}` : e.precision === 0 ? `${t}:[0-5]\\d` : `${t}:[0-5]\\d\\.\\d{${e.precision}}` : `${t}(?::[0-5]\\d(?:\\.\\d+)?)?`;
}
function xn(e) {
	return RegExp(`^${bn(e)}$`);
}
function Sn(e) {
	let t = bn({ precision: e.precision }), n = ["Z"];
	e.local && n.push(""), e.offset && n.push("([+-](?:[01]\\d|2[0-3]):[0-5]\\d)");
	let r = `${t}(?:${n.join("|")})`;
	return RegExp(`^${vn}T(?:${r})$`);
}
var Cn = (e) => {
	let t = e ? `[\\s\\S]{${e?.minimum ?? 0},${e?.maximum ?? ""}}` : "[\\s\\S]*";
	return RegExp(`^${t}$`);
}, wn = /^-?\d+$/, Tn = /^-?\d+(?:\.\d+)?$/, En = /^(?:true|false)$/i, Dn = /^[^A-Z]*$/, On = /^[^a-z]*$/, T = /*@__PURE__*/ b("$ZodCheck", (e, t) => {
	var n;
	e._zod ??= {}, e._zod.def = t, (n = e._zod).onattach ?? (n.onattach = []);
}), kn = {
	number: "number",
	bigint: "bigint",
	object: "date"
}, An = /*@__PURE__*/ b("$ZodCheckLessThan", (e, t) => {
	T.init(e, t);
	let n = kn[typeof t.value];
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
}), jn = /*@__PURE__*/ b("$ZodCheckGreaterThan", (e, t) => {
	T.init(e, t);
	let n = kn[typeof t.value];
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
}), Mn = /*@__PURE__*/ b("$ZodCheckMultipleOf", (e, t) => {
	T.init(e, t), e._zod.onattach.push((e) => {
		var n;
		(n = e._zod.bag).multipleOf ?? (n.multipleOf = t.value);
	}), e._zod.check = (n) => {
		if (typeof n.value != typeof t.value) throw Error("Cannot mix number and bigint in multiple_of check.");
		(typeof n.value == "bigint" ? n.value % t.value === BigInt(0) : rt(n.value, t.value) === 0) || n.issues.push({
			origin: typeof n.value,
			code: "not_multiple_of",
			divisor: t.value,
			input: n.value,
			inst: e,
			continue: !t.abort
		});
	};
}), Nn = /*@__PURE__*/ b("$ZodCheckNumberFormat", (e, t) => {
	T.init(e, t), t.format = t.format || "float64";
	let n = t.format?.includes("int"), r = n ? "int" : "number", [i, a] = vt[t.format];
	e._zod.onattach.push((e) => {
		let r = e._zod.bag;
		r.format = t.format, r.minimum = i, r.maximum = a, n && (r.pattern = wn);
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
}), Pn = /*@__PURE__*/ b("$ZodCheckMaxLength", (e, t) => {
	var n;
	T.init(e, t), (n = e._zod.def).when ?? (n.when = (e) => {
		let t = e.value;
		return !tt(t) && t.length !== void 0;
	}), e._zod.onattach.push((e) => {
		let n = e._zod.bag.maximum ?? Infinity;
		t.maximum < n && (e._zod.bag.maximum = t.maximum);
	}), e._zod.check = (n) => {
		let r = n.value;
		if (r.length <= t.maximum) return;
		let i = At(r);
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
}), Fn = /*@__PURE__*/ b("$ZodCheckMinLength", (e, t) => {
	var n;
	T.init(e, t), (n = e._zod.def).when ?? (n.when = (e) => {
		let t = e.value;
		return !tt(t) && t.length !== void 0;
	}), e._zod.onattach.push((e) => {
		let n = e._zod.bag.minimum ?? -Infinity;
		t.minimum > n && (e._zod.bag.minimum = t.minimum);
	}), e._zod.check = (n) => {
		let r = n.value;
		if (r.length >= t.minimum) return;
		let i = At(r);
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
}), In = /*@__PURE__*/ b("$ZodCheckLengthEquals", (e, t) => {
	var n;
	T.init(e, t), (n = e._zod.def).when ?? (n.when = (e) => {
		let t = e.value;
		return !tt(t) && t.length !== void 0;
	}), e._zod.onattach.push((e) => {
		let n = e._zod.bag;
		n.minimum = t.length, n.maximum = t.length, n.length = t.length;
	}), e._zod.check = (n) => {
		let r = n.value, i = r.length;
		if (i === t.length) return;
		let a = At(r), o = i > t.length;
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
}), Ln = /*@__PURE__*/ b("$ZodCheckStringFormat", (e, t) => {
	var n, r;
	T.init(e, t), e._zod.onattach.push((e) => {
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
}), Rn = /*@__PURE__*/ b("$ZodCheckRegex", (e, t) => {
	Ln.init(e, t), e._zod.check = (n) => {
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
}), zn = /*@__PURE__*/ b("$ZodCheckLowerCase", (e, t) => {
	t.pattern ??= Dn, Ln.init(e, t);
}), Bn = /*@__PURE__*/ b("$ZodCheckUpperCase", (e, t) => {
	t.pattern ??= On, Ln.init(e, t);
}), Vn = /*@__PURE__*/ b("$ZodCheckIncludes", (e, t) => {
	T.init(e, t);
	let n = ht(t.includes), r = new RegExp(typeof t.position == "number" ? `^.{${t.position}}${n}` : n);
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
}), Hn = /*@__PURE__*/ b("$ZodCheckStartsWith", (e, t) => {
	T.init(e, t);
	let n = RegExp(`^${ht(t.prefix)}.*`);
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
}), Un = /*@__PURE__*/ b("$ZodCheckEndsWith", (e, t) => {
	T.init(e, t);
	let n = RegExp(`.*${ht(t.suffix)}$`);
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
}), Wn = /*@__PURE__*/ b("$ZodCheckOverwrite", (e, t) => {
	T.init(e, t), e._zod.check = (e) => {
		e.value = t.tx(e.value);
	};
}), Gn = class {
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
}, Kn = {
	major: 4,
	minor: 4,
	patch: 3
}, E = /*@__PURE__*/ b("$ZodType", (e, t) => {
	var n;
	e ??= {}, e._zod.def = t, e._zod.bag = e._zod.bag || {}, e._zod.version = Kn;
	let r = [...e._zod.def.checks ?? []];
	e._zod.traits.has("$ZodCheck") && r.unshift(e);
	for (let t of r) for (let n of t._zod.onattach) n(e);
	if (r.length === 0) (n = e._zod).deferred ?? (n.deferred = []), e._zod.deferred?.push(() => {
		e._zod.run = e._zod.parse;
	});
	else {
		let t = (e, t, n) => {
			let r = Et(e), i;
			for (let a of t) {
				if (a._zod.def.when) {
					if (Dt(e) || !a._zod.def.when(e)) continue;
				} else if (r) continue;
				let t = e.issues.length, o = a._zod.check(e);
				if (o instanceof Promise && n?.async === !1) throw new Ye();
				if (i || o instanceof Promise) i = (i ?? Promise.resolve()).then(async () => {
					await o, e.issues.length !== t && (r ||= Et(e, t));
				});
				else {
					if (e.issues.length === t) continue;
					r ||= Et(e, t);
				}
			}
			return i ? i.then(() => e) : e;
		}, n = (n, i, a) => {
			if (Et(n)) return n.aborted = !0, n;
			let o = t(i, r, a);
			if (o instanceof Promise) {
				if (a.async === !1) throw new Ye();
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
				if (a.async === !1) throw new Ye();
				return o.then((e) => t(e, r, a));
			}
			return t(o, r, a);
		};
	}
	S(e, "~standard", () => ({
		validate: (t) => {
			try {
				let n = Bt(e, t);
				return n.success ? { value: n.data } : { issues: n.error?.issues };
			} catch {
				return Ht(e, t).then((e) => e.success ? { value: e.data } : { issues: e.error?.issues });
			}
		},
		vendor: "zod",
		version: 1
	}));
}), qn = /*@__PURE__*/ b("$ZodString", (e, t) => {
	E.init(e, t), e._zod.pattern = [...e?._zod.bag?.patterns ?? []].pop() ?? Cn(e._zod.bag), e._zod.parse = (n, r) => {
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
}), D = /*@__PURE__*/ b("$ZodStringFormat", (e, t) => {
	Ln.init(e, t), qn.init(e, t);
}), Jn = /*@__PURE__*/ b("$ZodGUID", (e, t) => {
	t.pattern ??= an, D.init(e, t);
}), Yn = /*@__PURE__*/ b("$ZodUUID", (e, t) => {
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
		t.pattern ??= on(e);
	} else t.pattern ??= on();
	D.init(e, t);
}), Xn = /*@__PURE__*/ b("$ZodEmail", (e, t) => {
	t.pattern ??= sn, D.init(e, t);
}), Zn = /*@__PURE__*/ b("$ZodURL", (e, t) => {
	D.init(e, t), e._zod.check = (n) => {
		try {
			let r = n.value.trim();
			if (!t.normalize && t.protocol?.source === gn.source && !/^https?:\/\//i.test(r)) {
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
}), Qn = /*@__PURE__*/ b("$ZodEmoji", (e, t) => {
	t.pattern ??= ln(), D.init(e, t);
}), $n = /*@__PURE__*/ b("$ZodNanoID", (e, t) => {
	t.pattern ??= nn, D.init(e, t);
}), er = /*@__PURE__*/ b("$ZodCUID", (e, t) => {
	t.pattern ??= Zt, D.init(e, t);
}), tr = /*@__PURE__*/ b("$ZodCUID2", (e, t) => {
	t.pattern ??= Qt, D.init(e, t);
}), nr = /*@__PURE__*/ b("$ZodULID", (e, t) => {
	t.pattern ??= $t, D.init(e, t);
}), rr = /*@__PURE__*/ b("$ZodXID", (e, t) => {
	t.pattern ??= en, D.init(e, t);
}), ir = /*@__PURE__*/ b("$ZodKSUID", (e, t) => {
	t.pattern ??= tn, D.init(e, t);
}), ar = /*@__PURE__*/ b("$ZodISODateTime", (e, t) => {
	t.pattern ??= Sn(t), D.init(e, t);
}), or = /*@__PURE__*/ b("$ZodISODate", (e, t) => {
	t.pattern ??= yn, D.init(e, t);
}), sr = /*@__PURE__*/ b("$ZodISOTime", (e, t) => {
	t.pattern ??= xn(t), D.init(e, t);
}), cr = /*@__PURE__*/ b("$ZodISODuration", (e, t) => {
	t.pattern ??= rn, D.init(e, t);
}), lr = /*@__PURE__*/ b("$ZodIPv4", (e, t) => {
	t.pattern ??= un, D.init(e, t), e._zod.bag.format = "ipv4";
}), ur = /*@__PURE__*/ b("$ZodIPv6", (e, t) => {
	t.pattern ??= dn, D.init(e, t), e._zod.bag.format = "ipv6", e._zod.check = (n) => {
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
}), dr = /*@__PURE__*/ b("$ZodCIDRv4", (e, t) => {
	t.pattern ??= fn, D.init(e, t);
}), fr = /*@__PURE__*/ b("$ZodCIDRv6", (e, t) => {
	t.pattern ??= pn, D.init(e, t), e._zod.check = (n) => {
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
function pr(e) {
	if (e === "") return !0;
	if (/\s/.test(e) || e.length % 4 != 0) return !1;
	try {
		return atob(e), !0;
	} catch {
		return !1;
	}
}
var mr = /*@__PURE__*/ b("$ZodBase64", (e, t) => {
	t.pattern ??= mn, D.init(e, t), e._zod.bag.contentEncoding = "base64", e._zod.check = (n) => {
		pr(n.value) || n.issues.push({
			code: "invalid_format",
			format: "base64",
			input: n.value,
			inst: e,
			continue: !t.abort
		});
	};
});
function hr(e) {
	if (!hn.test(e)) return !1;
	let t = e.replace(/[-_]/g, (e) => e === "-" ? "+" : "/");
	return pr(t.padEnd(Math.ceil(t.length / 4) * 4, "="));
}
var gr = /*@__PURE__*/ b("$ZodBase64URL", (e, t) => {
	t.pattern ??= hn, D.init(e, t), e._zod.bag.contentEncoding = "base64url", e._zod.check = (n) => {
		hr(n.value) || n.issues.push({
			code: "invalid_format",
			format: "base64url",
			input: n.value,
			inst: e,
			continue: !t.abort
		});
	};
}), _r = /*@__PURE__*/ b("$ZodE164", (e, t) => {
	t.pattern ??= _n, D.init(e, t);
});
function vr(e, t = null) {
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
var yr = /*@__PURE__*/ b("$ZodJWT", (e, t) => {
	D.init(e, t), e._zod.check = (n) => {
		vr(n.value, t.alg) || n.issues.push({
			code: "invalid_format",
			format: "jwt",
			input: n.value,
			inst: e,
			continue: !t.abort
		});
	};
}), br = /*@__PURE__*/ b("$ZodNumber", (e, t) => {
	E.init(e, t), e._zod.pattern = e._zod.bag.pattern ?? Tn, e._zod.parse = (n, r) => {
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
}), xr = /*@__PURE__*/ b("$ZodNumberFormat", (e, t) => {
	Nn.init(e, t), br.init(e, t);
}), Sr = /*@__PURE__*/ b("$ZodBoolean", (e, t) => {
	E.init(e, t), e._zod.pattern = En, e._zod.parse = (n, r) => {
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
}), Cr = /*@__PURE__*/ b("$ZodUnknown", (e, t) => {
	E.init(e, t), e._zod.parse = (e) => e;
}), wr = /*@__PURE__*/ b("$ZodNever", (e, t) => {
	E.init(e, t), e._zod.parse = (t, n) => (t.issues.push({
		expected: "never",
		code: "invalid_type",
		input: t.value,
		inst: e
	}), t);
});
function Tr(e, t, n) {
	e.issues.length && t.issues.push(...Ot(n, e.issues)), t.value[n] = e.value;
}
var Er = /*@__PURE__*/ b("$ZodArray", (e, t) => {
	E.init(e, t), e._zod.parse = (n, r) => {
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
			s instanceof Promise ? a.push(s.then((t) => Tr(t, n, e))) : Tr(s, n, e);
		}
		return a.length ? Promise.all(a).then(() => n) : n;
	};
});
function Dr(e, t, n, r, i, a) {
	let o = n in r;
	if (e.issues.length) {
		if (i && a && !o) return;
		t.issues.push(...Ot(n, e.issues));
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
function Or(e) {
	let t = Object.keys(e.shape);
	for (let n of t) if (!e.shape?.[n]?._zod?.traits?.has("$ZodType")) throw Error(`Invalid element at key "${n}": expected a Zod schema`);
	let n = _t(e.shape);
	return {
		...e,
		keys: t,
		keySet: new Set(t),
		numKeys: t.length,
		optionalKeys: new Set(n)
	};
}
function kr(e, t, n, r, i, a) {
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
		a instanceof Promise ? e.push(a.then((e) => Dr(e, n, i, t, u, d))) : Dr(a, n, i, t, u, d);
	}
	return o.length && n.issues.push({
		code: "unrecognized_keys",
		keys: o,
		input: t,
		inst: a
	}), e.length ? Promise.all(e).then(() => n) : n;
}
var Ar = /*@__PURE__*/ b("$ZodObject", (e, t) => {
	if (E.init(e, t), !Object.getOwnPropertyDescriptor(t, "shape")?.get) {
		let e = t.shape;
		Object.defineProperty(t, "shape", { get: () => {
			let n = { ...e };
			return Object.defineProperty(t, "shape", { value: n }), n;
		} });
	}
	let n = et(() => Or(t));
	S(e._zod, "propValues", () => {
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
	let r = ut, i = t.catchall, a;
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
			a instanceof Promise ? c.push(a.then((n) => Dr(n, t, e, s, r, i))) : Dr(a, t, e, s, r, i);
		}
		return i ? kr(c, s, t, o, n.value, e) : c.length ? Promise.all(c).then(() => t) : t;
	};
}), jr = /*@__PURE__*/ b("$ZodObjectJIT", (e, t) => {
	Ar.init(e, t);
	let n = e._zod.parse, r = et(() => Or(t)), i = (e) => {
		let t = new Gn([
			"shape",
			"payload",
			"ctx"
		]), n = r.value, i = (e) => {
			let t = st(e);
			return `shape[${t}]._zod.run({ value: input[${t}], issues: [] }, ctx)`;
		};
		t.write("const input = payload.value;");
		let a = Object.create(null), o = 0;
		for (let e of n.keys) a[e] = `key_${o++}`;
		t.write("const newResult = {};");
		for (let r of n.keys) {
			let n = a[r], o = st(r), s = e[r], c = s?._zod?.optin === "optional", l = s?._zod?.optout === "optional";
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
	}, a, o = ut, s = !Ze.jitless, c = s && dt.value, l = t.catchall, u;
	e._zod.parse = (d, f) => {
		u ??= r.value;
		let p = d.value;
		return o(p) ? s && c && f?.async === !1 && f.jitless !== !0 ? (a ||= i(t.shape), d = a(d, f), l ? kr([], p, d, f, u, e) : d) : n(d, f) : (d.issues.push({
			expected: "object",
			code: "invalid_type",
			input: p,
			inst: e
		}), d);
	};
});
function Mr(e, t, n, r) {
	for (let n of e) if (n.issues.length === 0) return t.value = n.value, t;
	let i = e.filter((e) => !Et(e));
	return i.length === 1 ? (t.value = i[0].value, i[0]) : (t.issues.push({
		code: "invalid_union",
		input: t.value,
		inst: n,
		errors: e.map((e) => e.issues.map((e) => w(e, r, x())))
	}), t);
}
var Nr = /*@__PURE__*/ b("$ZodUnion", (e, t) => {
	E.init(e, t), S(e._zod, "optin", () => t.options.some((e) => e._zod.optin === "optional") ? "optional" : void 0), S(e._zod, "optout", () => t.options.some((e) => e._zod.optout === "optional") ? "optional" : void 0), S(e._zod, "values", () => {
		if (t.options.every((e) => e._zod.values)) return new Set(t.options.flatMap((e) => Array.from(e._zod.values)));
	}), S(e._zod, "pattern", () => {
		if (t.options.every((e) => e._zod.pattern)) {
			let e = t.options.map((e) => e._zod.pattern);
			return RegExp(`^(${e.map((e) => nt(e.source)).join("|")})$`);
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
		return a ? Promise.all(o).then((t) => Mr(t, r, e, i)) : Mr(o, r, e, i);
	};
}), Pr = /*@__PURE__*/ b("$ZodIntersection", (e, t) => {
	E.init(e, t), e._zod.parse = (e, n) => {
		let r = e.value, i = t.left._zod.run({
			value: r,
			issues: []
		}, n), a = t.right._zod.run({
			value: r,
			issues: []
		}, n);
		return i instanceof Promise || a instanceof Promise ? Promise.all([i, a]).then(([t, n]) => Ir(e, t, n)) : Ir(e, i, a);
	};
});
function Fr(e, t) {
	if (e === t || e instanceof Date && t instanceof Date && +e == +t) return {
		valid: !0,
		data: e
	};
	if (ft(e) && ft(t)) {
		let n = Object.keys(t), r = Object.keys(e).filter((e) => n.indexOf(e) !== -1), i = {
			...e,
			...t
		};
		for (let n of r) {
			let r = Fr(e[n], t[n]);
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
			let i = e[r], a = t[r], o = Fr(i, a);
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
function Ir(e, t, n) {
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
	}), Et(e)) return e;
	let o = Fr(t.value, n.value);
	if (!o.valid) throw Error(`Unmergable intersection. Error path: ${JSON.stringify(o.mergeErrorPath)}`);
	return e.value = o.data, e;
}
var Lr = /*@__PURE__*/ b("$ZodRecord", (e, t) => {
	E.init(e, t), e._zod.parse = (n, r) => {
		let i = n.value;
		if (!ft(i)) return n.issues.push({
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
						issues: o.issues.map((e) => w(e, r, x())),
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
					e.issues.length && n.issues.push(...Ot(c, e.issues)), n.value[l] = e.value;
				})) : (u.issues.length && n.issues.push(...Ot(c, u.issues)), n.value[l] = u.value);
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
				if (typeof o == "string" && Tn.test(o) && s.issues.length) {
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
						issues: s.issues.map((e) => w(e, r, x())),
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
					e.issues.length && n.issues.push(...Ot(o, e.issues)), n.value[s.value] = e.value;
				})) : (c.issues.length && n.issues.push(...Ot(o, c.issues)), n.value[s.value] = c.value);
			}
		}
		return a.length ? Promise.all(a).then(() => n) : n;
	};
}), Rr = /*@__PURE__*/ b("$ZodEnum", (e, t) => {
	E.init(e, t);
	let n = Qe(t.entries), r = new Set(n);
	e._zod.values = r, e._zod.pattern = RegExp(`^(${n.filter((e) => mt.has(typeof e)).map((e) => typeof e == "string" ? ht(e) : e.toString()).join("|")})$`), e._zod.parse = (t, i) => {
		let a = t.value;
		return r.has(a) || t.issues.push({
			code: "invalid_value",
			values: n,
			input: a,
			inst: e
		}), t;
	};
}), zr = /*@__PURE__*/ b("$ZodLiteral", (e, t) => {
	if (E.init(e, t), t.values.length === 0) throw Error("Cannot create literal schema with no valid values");
	let n = new Set(t.values);
	e._zod.values = n, e._zod.pattern = RegExp(`^(${t.values.map((e) => typeof e == "string" ? ht(e) : e ? ht(e.toString()) : String(e)).join("|")})$`), e._zod.parse = (r, i) => {
		let a = r.value;
		return n.has(a) || r.issues.push({
			code: "invalid_value",
			values: t.values,
			input: a,
			inst: e
		}), r;
	};
}), Br = /*@__PURE__*/ b("$ZodTransform", (e, t) => {
	E.init(e, t), e._zod.optin = "optional", e._zod.parse = (n, r) => {
		if (r.direction === "backward") throw new Xe(e.constructor.name);
		let i = t.transform(n.value, n);
		if (r.async) return (i instanceof Promise ? i : Promise.resolve(i)).then((e) => (n.value = e, n.fallback = !0, n));
		if (i instanceof Promise) throw new Ye();
		return n.value = i, n.fallback = !0, n;
	};
});
function Vr(e, t) {
	return t === void 0 && (e.issues.length || e.fallback) ? {
		issues: [],
		value: void 0
	} : e;
}
var Hr = /*@__PURE__*/ b("$ZodOptional", (e, t) => {
	E.init(e, t), e._zod.optin = "optional", e._zod.optout = "optional", S(e._zod, "values", () => t.innerType._zod.values ? /* @__PURE__ */ new Set([...t.innerType._zod.values, void 0]) : void 0), S(e._zod, "pattern", () => {
		let e = t.innerType._zod.pattern;
		return e ? RegExp(`^(${nt(e.source)})?$`) : void 0;
	}), e._zod.parse = (e, n) => {
		if (t.innerType._zod.optin === "optional") {
			let r = e.value, i = t.innerType._zod.run(e, n);
			return i instanceof Promise ? i.then((e) => Vr(e, r)) : Vr(i, r);
		}
		return e.value === void 0 ? e : t.innerType._zod.run(e, n);
	};
}), Ur = /*@__PURE__*/ b("$ZodExactOptional", (e, t) => {
	Hr.init(e, t), S(e._zod, "values", () => t.innerType._zod.values), S(e._zod, "pattern", () => t.innerType._zod.pattern), e._zod.parse = (e, n) => t.innerType._zod.run(e, n);
}), Wr = /*@__PURE__*/ b("$ZodNullable", (e, t) => {
	E.init(e, t), S(e._zod, "optin", () => t.innerType._zod.optin), S(e._zod, "optout", () => t.innerType._zod.optout), S(e._zod, "pattern", () => {
		let e = t.innerType._zod.pattern;
		return e ? RegExp(`^(${nt(e.source)}|null)$`) : void 0;
	}), S(e._zod, "values", () => t.innerType._zod.values ? /* @__PURE__ */ new Set([...t.innerType._zod.values, null]) : void 0), e._zod.parse = (e, n) => e.value === null ? e : t.innerType._zod.run(e, n);
}), Gr = /*@__PURE__*/ b("$ZodDefault", (e, t) => {
	E.init(e, t), e._zod.optin = "optional", S(e._zod, "values", () => t.innerType._zod.values), e._zod.parse = (e, n) => {
		if (n.direction === "backward") return t.innerType._zod.run(e, n);
		if (e.value === void 0) return e.value = t.defaultValue, e;
		let r = t.innerType._zod.run(e, n);
		return r instanceof Promise ? r.then((e) => Kr(e, t)) : Kr(r, t);
	};
});
function Kr(e, t) {
	return e.value === void 0 && (e.value = t.defaultValue), e;
}
var qr = /*@__PURE__*/ b("$ZodPrefault", (e, t) => {
	E.init(e, t), e._zod.optin = "optional", S(e._zod, "values", () => t.innerType._zod.values), e._zod.parse = (e, n) => (n.direction === "backward" || e.value === void 0 && (e.value = t.defaultValue), t.innerType._zod.run(e, n));
}), Jr = /*@__PURE__*/ b("$ZodNonOptional", (e, t) => {
	E.init(e, t), S(e._zod, "values", () => {
		let e = t.innerType._zod.values;
		return e ? new Set([...e].filter((e) => e !== void 0)) : void 0;
	}), e._zod.parse = (n, r) => {
		let i = t.innerType._zod.run(n, r);
		return i instanceof Promise ? i.then((t) => Yr(t, e)) : Yr(i, e);
	};
});
function Yr(e, t) {
	return !e.issues.length && e.value === void 0 && e.issues.push({
		code: "invalid_type",
		expected: "nonoptional",
		input: e.value,
		inst: t
	}), e;
}
var Xr = /*@__PURE__*/ b("$ZodCatch", (e, t) => {
	E.init(e, t), e._zod.optin = "optional", S(e._zod, "optout", () => t.innerType._zod.optout), S(e._zod, "values", () => t.innerType._zod.values), e._zod.parse = (e, n) => {
		if (n.direction === "backward") return t.innerType._zod.run(e, n);
		let r = t.innerType._zod.run(e, n);
		return r instanceof Promise ? r.then((r) => (e.value = r.value, r.issues.length && (e.value = t.catchValue({
			...e,
			error: { issues: r.issues.map((e) => w(e, n, x())) },
			input: e.value
		}), e.issues = [], e.fallback = !0), e)) : (e.value = r.value, r.issues.length && (e.value = t.catchValue({
			...e,
			error: { issues: r.issues.map((e) => w(e, n, x())) },
			input: e.value
		}), e.issues = [], e.fallback = !0), e);
	};
}), Zr = /*@__PURE__*/ b("$ZodPipe", (e, t) => {
	E.init(e, t), S(e._zod, "values", () => t.in._zod.values), S(e._zod, "optin", () => t.in._zod.optin), S(e._zod, "optout", () => t.out._zod.optout), S(e._zod, "propValues", () => t.in._zod.propValues), e._zod.parse = (e, n) => {
		if (n.direction === "backward") {
			let r = t.out._zod.run(e, n);
			return r instanceof Promise ? r.then((e) => Qr(e, t.in, n)) : Qr(r, t.in, n);
		}
		let r = t.in._zod.run(e, n);
		return r instanceof Promise ? r.then((e) => Qr(e, t.out, n)) : Qr(r, t.out, n);
	};
});
function Qr(e, t, n) {
	return e.issues.length ? (e.aborted = !0, e) : t._zod.run({
		value: e.value,
		issues: e.issues,
		fallback: e.fallback
	}, n);
}
var $r = /*@__PURE__*/ b("$ZodReadonly", (e, t) => {
	E.init(e, t), S(e._zod, "propValues", () => t.innerType._zod.propValues), S(e._zod, "values", () => t.innerType._zod.values), S(e._zod, "optin", () => t.innerType?._zod?.optin), S(e._zod, "optout", () => t.innerType?._zod?.optout), e._zod.parse = (e, n) => {
		if (n.direction === "backward") return t.innerType._zod.run(e, n);
		let r = t.innerType._zod.run(e, n);
		return r instanceof Promise ? r.then(ei) : ei(r);
	};
});
function ei(e) {
	return e.value = Object.freeze(e.value), e;
}
var ti = /*@__PURE__*/ b("$ZodCustom", (e, t) => {
	T.init(e, t), E.init(e, t), e._zod.parse = (e, t) => e, e._zod.check = (n) => {
		let r = n.value, i = t.fn(r);
		if (i instanceof Promise) return i.then((t) => ni(t, n, r, e));
		ni(i, n, r, e);
	};
});
function ni(e, t, n, r) {
	if (!e) {
		let e = {
			code: "custom",
			input: n,
			inst: r,
			path: [...r._zod.def.path ?? []],
			continue: !r._zod.def.abort
		};
		r._zod.def.params && (e.params = r._zod.def.params), t.issues.push(jt(e));
	}
}
//#endregion
//#region node_modules/.pnpm/zod@4.4.3/node_modules/zod/v4/core/registries.js
var ri, ii = class {
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
function ai() {
	return new ii();
}
(ri = globalThis).__zod_globalRegistry ?? (ri.__zod_globalRegistry = ai());
var oi = globalThis.__zod_globalRegistry;
//#endregion
//#region node_modules/.pnpm/zod@4.4.3/node_modules/zod/v4/core/api.js
// @__NO_SIDE_EFFECTS__
function si(e, t) {
	return new e({
		type: "string",
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function ci(e, t) {
	return new e({
		type: "string",
		format: "email",
		check: "string_format",
		abort: !1,
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function li(e, t) {
	return new e({
		type: "string",
		format: "guid",
		check: "string_format",
		abort: !1,
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function ui(e, t) {
	return new e({
		type: "string",
		format: "uuid",
		check: "string_format",
		abort: !1,
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function di(e, t) {
	return new e({
		type: "string",
		format: "uuid",
		check: "string_format",
		abort: !1,
		version: "v4",
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function fi(e, t) {
	return new e({
		type: "string",
		format: "uuid",
		check: "string_format",
		abort: !1,
		version: "v6",
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function pi(e, t) {
	return new e({
		type: "string",
		format: "uuid",
		check: "string_format",
		abort: !1,
		version: "v7",
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function mi(e, t) {
	return new e({
		type: "string",
		format: "url",
		check: "string_format",
		abort: !1,
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function hi(e, t) {
	return new e({
		type: "string",
		format: "emoji",
		check: "string_format",
		abort: !1,
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function gi(e, t) {
	return new e({
		type: "string",
		format: "nanoid",
		check: "string_format",
		abort: !1,
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function _i(e, t) {
	return new e({
		type: "string",
		format: "cuid",
		check: "string_format",
		abort: !1,
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function vi(e, t) {
	return new e({
		type: "string",
		format: "cuid2",
		check: "string_format",
		abort: !1,
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function yi(e, t) {
	return new e({
		type: "string",
		format: "ulid",
		check: "string_format",
		abort: !1,
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function bi(e, t) {
	return new e({
		type: "string",
		format: "xid",
		check: "string_format",
		abort: !1,
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function xi(e, t) {
	return new e({
		type: "string",
		format: "ksuid",
		check: "string_format",
		abort: !1,
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Si(e, t) {
	return new e({
		type: "string",
		format: "ipv4",
		check: "string_format",
		abort: !1,
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Ci(e, t) {
	return new e({
		type: "string",
		format: "ipv6",
		check: "string_format",
		abort: !1,
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function wi(e, t) {
	return new e({
		type: "string",
		format: "cidrv4",
		check: "string_format",
		abort: !1,
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Ti(e, t) {
	return new e({
		type: "string",
		format: "cidrv6",
		check: "string_format",
		abort: !1,
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Ei(e, t) {
	return new e({
		type: "string",
		format: "base64",
		check: "string_format",
		abort: !1,
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Di(e, t) {
	return new e({
		type: "string",
		format: "base64url",
		check: "string_format",
		abort: !1,
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Oi(e, t) {
	return new e({
		type: "string",
		format: "e164",
		check: "string_format",
		abort: !1,
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function ki(e, t) {
	return new e({
		type: "string",
		format: "jwt",
		check: "string_format",
		abort: !1,
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Ai(e, t) {
	return new e({
		type: "string",
		format: "datetime",
		check: "string_format",
		offset: !1,
		local: !1,
		precision: null,
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function ji(e, t) {
	return new e({
		type: "string",
		format: "date",
		check: "string_format",
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Mi(e, t) {
	return new e({
		type: "string",
		format: "time",
		check: "string_format",
		precision: null,
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Ni(e, t) {
	return new e({
		type: "string",
		format: "duration",
		check: "string_format",
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Pi(e, t) {
	return new e({
		type: "number",
		checks: [],
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Fi(e, t) {
	return new e({
		type: "number",
		check: "number_format",
		abort: !1,
		format: "safeint",
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Ii(e, t) {
	return new e({
		type: "boolean",
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function Li(e) {
	return new e({ type: "unknown" });
}
// @__NO_SIDE_EFFECTS__
function Ri(e, t) {
	return new e({
		type: "never",
		...C(t)
	});
}
// @__NO_SIDE_EFFECTS__
function zi(e, t) {
	return new An({
		check: "less_than",
		...C(t),
		value: e,
		inclusive: !1
	});
}
// @__NO_SIDE_EFFECTS__
function Bi(e, t) {
	return new An({
		check: "less_than",
		...C(t),
		value: e,
		inclusive: !0
	});
}
// @__NO_SIDE_EFFECTS__
function Vi(e, t) {
	return new jn({
		check: "greater_than",
		...C(t),
		value: e,
		inclusive: !1
	});
}
// @__NO_SIDE_EFFECTS__
function Hi(e, t) {
	return new jn({
		check: "greater_than",
		...C(t),
		value: e,
		inclusive: !0
	});
}
// @__NO_SIDE_EFFECTS__
function Ui(e, t) {
	return new Mn({
		check: "multiple_of",
		...C(t),
		value: e
	});
}
// @__NO_SIDE_EFFECTS__
function Wi(e, t) {
	return new Pn({
		check: "max_length",
		...C(t),
		maximum: e
	});
}
// @__NO_SIDE_EFFECTS__
function Gi(e, t) {
	return new Fn({
		check: "min_length",
		...C(t),
		minimum: e
	});
}
// @__NO_SIDE_EFFECTS__
function Ki(e, t) {
	return new In({
		check: "length_equals",
		...C(t),
		length: e
	});
}
// @__NO_SIDE_EFFECTS__
function qi(e, t) {
	return new Rn({
		check: "string_format",
		format: "regex",
		...C(t),
		pattern: e
	});
}
// @__NO_SIDE_EFFECTS__
function Ji(e) {
	return new zn({
		check: "string_format",
		format: "lowercase",
		...C(e)
	});
}
// @__NO_SIDE_EFFECTS__
function Yi(e) {
	return new Bn({
		check: "string_format",
		format: "uppercase",
		...C(e)
	});
}
// @__NO_SIDE_EFFECTS__
function Xi(e, t) {
	return new Vn({
		check: "string_format",
		format: "includes",
		...C(t),
		includes: e
	});
}
// @__NO_SIDE_EFFECTS__
function Zi(e, t) {
	return new Hn({
		check: "string_format",
		format: "starts_with",
		...C(t),
		prefix: e
	});
}
// @__NO_SIDE_EFFECTS__
function Qi(e, t) {
	return new Un({
		check: "string_format",
		format: "ends_with",
		...C(t),
		suffix: e
	});
}
// @__NO_SIDE_EFFECTS__
function $i(e) {
	return new Wn({
		check: "overwrite",
		tx: e
	});
}
// @__NO_SIDE_EFFECTS__
function ea(e) {
	return /* @__PURE__ */ $i((t) => t.normalize(e));
}
// @__NO_SIDE_EFFECTS__
function ta() {
	return /* @__PURE__ */ $i((e) => e.trim());
}
// @__NO_SIDE_EFFECTS__
function na() {
	return /* @__PURE__ */ $i((e) => e.toLowerCase());
}
// @__NO_SIDE_EFFECTS__
function ra() {
	return /* @__PURE__ */ $i((e) => e.toUpperCase());
}
// @__NO_SIDE_EFFECTS__
function ia() {
	return /* @__PURE__ */ $i((e) => ct(e));
}
// @__NO_SIDE_EFFECTS__
function aa(e, t, n) {
	return new e({
		type: "array",
		element: t,
		...C(n)
	});
}
// @__NO_SIDE_EFFECTS__
function oa(e, t, n) {
	return new e({
		type: "custom",
		check: "custom",
		fn: t,
		...C(n)
	});
}
// @__NO_SIDE_EFFECTS__
function sa(e, t) {
	let n = /* @__PURE__ */ ca((t) => (t.addIssue = (e) => {
		if (typeof e == "string") t.issues.push(jt(e, t.value, n._zod.def));
		else {
			let r = e;
			r.fatal && (r.continue = !1), r.code ??= "custom", r.input ??= t.value, r.inst ??= n, r.continue ??= !n._zod.def.abort, t.issues.push(jt(r));
		}
	}, e(t.value, t)), t);
	return n;
}
// @__NO_SIDE_EFFECTS__
function ca(e, t) {
	let n = new T({
		check: "custom",
		...C(t)
	});
	return n._zod.check = e, n;
}
//#endregion
//#region node_modules/.pnpm/zod@4.4.3/node_modules/zod/v4/core/to-json-schema.js
function la(e) {
	let t = e?.target ?? "draft-2020-12";
	return t === "draft-4" && (t = "draft-04"), t === "draft-7" && (t = "draft-07"), {
		processors: e.processors ?? {},
		metadataRegistry: e?.metadata ?? oi,
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
function O(e, t, n = {
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
		a && (o.ref ||= a, O(a, t, r), t.seen.get(a).isParent = !0);
	}
	let c = t.metadataRegistry.get(e);
	return c && Object.assign(o.schema, c), t.io === "input" && k(e) && (delete o.schema.examples, delete o.schema.default), t.io === "input" && "_prefault" in o.schema && ((r = o.schema).default ?? (r.default = o.schema._prefault)), delete o.schema._prefault, t.seen.get(e).schema;
}
function ua(e, t) {
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
function da(e, t) {
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
					input: pa(t, "input", e.processors),
					output: pa(t, "output", e.processors)
				}
			},
			enumerable: !1,
			writable: !1
		}), n;
	} catch {
		throw Error("Error converting schema to JSON.");
	}
}
function k(e, t) {
	let n = t ?? { seen: /* @__PURE__ */ new Set() };
	if (n.seen.has(e)) return !1;
	n.seen.add(e);
	let r = e._zod.def;
	if (r.type === "transform") return !0;
	if (r.type === "array") return k(r.element, n);
	if (r.type === "set") return k(r.valueType, n);
	if (r.type === "lazy") return k(r.getter(), n);
	if (r.type === "promise" || r.type === "optional" || r.type === "nonoptional" || r.type === "nullable" || r.type === "readonly" || r.type === "default" || r.type === "prefault") return k(r.innerType, n);
	if (r.type === "intersection") return k(r.left, n) || k(r.right, n);
	if (r.type === "record" || r.type === "map") return k(r.keyType, n) || k(r.valueType, n);
	if (r.type === "pipe") return e._zod.traits.has("$ZodCodec") ? !0 : k(r.in, n) || k(r.out, n);
	if (r.type === "object") {
		for (let e in r.shape) if (k(r.shape[e], n)) return !0;
		return !1;
	}
	if (r.type === "union") {
		for (let e of r.options) if (k(e, n)) return !0;
		return !1;
	}
	if (r.type === "tuple") {
		for (let e of r.items) if (k(e, n)) return !0;
		return !!(r.rest && k(r.rest, n));
	}
	return !1;
}
var fa = (e, t = {}) => (n) => {
	let r = la({
		...n,
		processors: t
	});
	return O(e, r), ua(r, e), da(r, e);
}, pa = (e, t, n = {}) => (r) => {
	let { libraryOptions: i, target: a } = r ?? {}, o = la({
		...i ?? {},
		target: a,
		io: t,
		processors: n
	});
	return O(e, o), ua(o, e), da(o, e);
}, ma = {
	guid: "uuid",
	url: "uri",
	datetime: "date-time",
	json_string: "json-string",
	regex: ""
}, ha = (e, t, n, r) => {
	let i = n;
	i.type = "string";
	let { minimum: a, maximum: o, format: s, patterns: c, contentEncoding: l } = e._zod.bag;
	if (typeof a == "number" && (i.minLength = a), typeof o == "number" && (i.maxLength = o), s && (i.format = ma[s] ?? s, i.format === "" && delete i.format, s === "time" && delete i.format), l && (i.contentEncoding = l), c && c.size > 0) {
		let e = [...c];
		e.length === 1 ? i.pattern = e[0].source : e.length > 1 && (i.allOf = [...e.map((e) => ({
			...t.target === "draft-07" || t.target === "draft-04" || t.target === "openapi-3.0" ? { type: "string" } : {},
			pattern: e.source
		}))]);
	}
}, ga = (e, t, n, r) => {
	let i = n, { minimum: a, maximum: o, format: s, multipleOf: c, exclusiveMaximum: l, exclusiveMinimum: u } = e._zod.bag;
	i.type = typeof s == "string" && s.includes("int") ? "integer" : "number";
	let d = typeof u == "number" && u >= (a ?? -Infinity), f = typeof l == "number" && l <= (o ?? Infinity), p = t.target === "draft-04" || t.target === "openapi-3.0";
	d ? p ? (i.minimum = u, i.exclusiveMinimum = !0) : i.exclusiveMinimum = u : typeof a == "number" && (i.minimum = a), f ? p ? (i.maximum = l, i.exclusiveMaximum = !0) : i.exclusiveMaximum = l : typeof o == "number" && (i.maximum = o), typeof c == "number" && (i.multipleOf = c);
}, _a = (e, t, n, r) => {
	n.type = "boolean";
}, va = (e, t, n, r) => {
	n.not = {};
}, ya = (e, t, n, r) => {
	let i = e._zod.def, a = Qe(i.entries);
	a.every((e) => typeof e == "number") && (n.type = "number"), a.every((e) => typeof e == "string") && (n.type = "string"), n.enum = a;
}, ba = (e, t, n, r) => {
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
}, xa = (e, t, n, r) => {
	if (t.unrepresentable === "throw") throw Error("Custom types cannot be represented in JSON Schema");
}, Sa = (e, t, n, r) => {
	if (t.unrepresentable === "throw") throw Error("Transforms cannot be represented in JSON Schema");
}, Ca = (e, t, n, r) => {
	let i = n, a = e._zod.def, { minimum: o, maximum: s } = e._zod.bag;
	typeof o == "number" && (i.minItems = o), typeof s == "number" && (i.maxItems = s), i.type = "array", i.items = O(a.element, t, {
		...r,
		path: [...r.path, "items"]
	});
}, wa = (e, t, n, r) => {
	let i = n, a = e._zod.def;
	i.type = "object", i.properties = {};
	let o = a.shape;
	for (let e in o) i.properties[e] = O(o[e], t, {
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
	c.size > 0 && (i.required = Array.from(c)), a.catchall?._zod.def.type === "never" ? i.additionalProperties = !1 : a.catchall ? a.catchall && (i.additionalProperties = O(a.catchall, t, {
		...r,
		path: [...r.path, "additionalProperties"]
	})) : t.io === "output" && (i.additionalProperties = !1);
}, Ta = (e, t, n, r) => {
	let i = e._zod.def, a = i.inclusive === !1, o = i.options.map((e, n) => O(e, t, {
		...r,
		path: [
			...r.path,
			a ? "oneOf" : "anyOf",
			n
		]
	}));
	a ? n.oneOf = o : n.anyOf = o;
}, Ea = (e, t, n, r) => {
	let i = e._zod.def, a = O(i.left, t, {
		...r,
		path: [
			...r.path,
			"allOf",
			0
		]
	}), o = O(i.right, t, {
		...r,
		path: [
			...r.path,
			"allOf",
			1
		]
	}), s = (e) => "allOf" in e && Object.keys(e).length === 1;
	n.allOf = [...s(a) ? a.allOf : [a], ...s(o) ? o.allOf : [o]];
}, Da = (e, t, n, r) => {
	let i = n, a = e._zod.def;
	i.type = "object";
	let o = a.keyType, s = o._zod.bag?.patterns;
	if (a.mode === "loose" && s && s.size > 0) {
		let e = O(a.valueType, t, {
			...r,
			path: [
				...r.path,
				"patternProperties",
				"*"
			]
		});
		i.patternProperties = {};
		for (let t of s) i.patternProperties[t.source] = e;
	} else (t.target === "draft-07" || t.target === "draft-2020-12") && (i.propertyNames = O(a.keyType, t, {
		...r,
		path: [...r.path, "propertyNames"]
	})), i.additionalProperties = O(a.valueType, t, {
		...r,
		path: [...r.path, "additionalProperties"]
	});
	let c = o._zod.values;
	if (c) {
		let e = [...c].filter((e) => typeof e == "string" || typeof e == "number");
		e.length > 0 && (i.required = e);
	}
}, Oa = (e, t, n, r) => {
	let i = e._zod.def, a = O(i.innerType, t, r), o = t.seen.get(e);
	t.target === "openapi-3.0" ? (o.ref = i.innerType, n.nullable = !0) : n.anyOf = [a, { type: "null" }];
}, ka = (e, t, n, r) => {
	let i = e._zod.def;
	O(i.innerType, t, r);
	let a = t.seen.get(e);
	a.ref = i.innerType;
}, Aa = (e, t, n, r) => {
	let i = e._zod.def;
	O(i.innerType, t, r);
	let a = t.seen.get(e);
	a.ref = i.innerType, n.default = JSON.parse(JSON.stringify(i.defaultValue));
}, ja = (e, t, n, r) => {
	let i = e._zod.def;
	O(i.innerType, t, r);
	let a = t.seen.get(e);
	a.ref = i.innerType, t.io === "input" && (n._prefault = JSON.parse(JSON.stringify(i.defaultValue)));
}, Ma = (e, t, n, r) => {
	let i = e._zod.def;
	O(i.innerType, t, r);
	let a = t.seen.get(e);
	a.ref = i.innerType;
	let o;
	try {
		o = i.catchValue(void 0);
	} catch {
		throw Error("Dynamic catch values are not supported in JSON Schema");
	}
	n.default = o;
}, Na = (e, t, n, r) => {
	let i = e._zod.def, a = i.in._zod.traits.has("$ZodTransform"), o = t.io === "input" ? a ? i.out : i.in : i.out;
	O(o, t, r);
	let s = t.seen.get(e);
	s.ref = o;
}, Pa = (e, t, n, r) => {
	let i = e._zod.def;
	O(i.innerType, t, r);
	let a = t.seen.get(e);
	a.ref = i.innerType, n.readOnly = !0;
}, Fa = (e, t, n, r) => {
	let i = e._zod.def;
	O(i.innerType, t, r);
	let a = t.seen.get(e);
	a.ref = i.innerType;
}, Ia = /*@__PURE__*/ b("ZodISODateTime", (e, t) => {
	ar.init(e, t), N.init(e, t);
});
function La(e) {
	return /* @__PURE__ */ Ai(Ia, e);
}
var Ra = /*@__PURE__*/ b("ZodISODate", (e, t) => {
	or.init(e, t), N.init(e, t);
});
function za(e) {
	return /* @__PURE__ */ ji(Ra, e);
}
var Ba = /*@__PURE__*/ b("ZodISOTime", (e, t) => {
	sr.init(e, t), N.init(e, t);
});
function Va(e) {
	return /* @__PURE__ */ Mi(Ba, e);
}
var Ha = /*@__PURE__*/ b("ZodISODuration", (e, t) => {
	cr.init(e, t), N.init(e, t);
});
function Ua(e) {
	return /* @__PURE__ */ Ni(Ha, e);
}
var A = /*@__PURE__*/ b("ZodError", (e, t) => {
	Nt.init(e, t), e.name = "ZodError", Object.defineProperties(e, {
		format: { value: (t) => It(e, t) },
		flatten: { value: (t) => Ft(e, t) },
		addIssue: { value: (t) => {
			e.issues.push(t), e.message = JSON.stringify(e.issues, $e, 2);
		} },
		addIssues: { value: (t) => {
			e.issues.push(...t), e.message = JSON.stringify(e.issues, $e, 2);
		} },
		isEmpty: { get() {
			return e.issues.length === 0;
		} }
	});
}, { Parent: Error }), Wa = /* @__PURE__ */ Lt(A), Ga = /* @__PURE__ */ Rt(A), Ka = /* @__PURE__ */ zt(A), qa = /* @__PURE__ */ Vt(A), Ja = /* @__PURE__ */ Ut(A), Ya = /* @__PURE__ */ Wt(A), Xa = /* @__PURE__ */ Gt(A), Za = /* @__PURE__ */ Kt(A), Qa = /* @__PURE__ */ qt(A), $a = /* @__PURE__ */ Jt(A), eo = /* @__PURE__ */ Yt(A), to = /* @__PURE__ */ Xt(A), no = /* @__PURE__ */ new WeakMap();
function ro(e, t, n) {
	let r = Object.getPrototypeOf(e), i = no.get(r);
	if (i || (i = /* @__PURE__ */ new Set(), no.set(r, i)), !i.has(t)) {
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
var j = /*@__PURE__*/ b("ZodType", (e, t) => (E.init(e, t), Object.assign(e["~standard"], { jsonSchema: {
	input: pa(e, "input"),
	output: pa(e, "output")
} }), e.toJSONSchema = fa(e, {}), e.def = t, e.type = t.type, Object.defineProperty(e, "_def", { value: t }), e.parse = (t, n) => Wa(e, t, n, { callee: e.parse }), e.safeParse = (t, n) => Ka(e, t, n), e.parseAsync = async (t, n) => Ga(e, t, n, { callee: e.parseAsync }), e.safeParseAsync = async (t, n) => qa(e, t, n), e.spa = e.safeParseAsync, e.encode = (t, n) => Ja(e, t, n), e.decode = (t, n) => Ya(e, t, n), e.encodeAsync = async (t, n) => Xa(e, t, n), e.decodeAsync = async (t, n) => Za(e, t, n), e.safeEncode = (t, n) => Qa(e, t, n), e.safeDecode = (t, n) => $a(e, t, n), e.safeEncodeAsync = async (t, n) => eo(e, t, n), e.safeDecodeAsync = async (t, n) => to(e, t, n), ro(e, "ZodType", {
	check(...e) {
		let t = this.def;
		return this.clone(ot(t, { checks: [...t.checks ?? [], ...e.map((e) => typeof e == "function" ? { _zod: {
			check: e,
			def: { check: "custom" },
			onattach: []
		} } : e)] }), { parent: !0 });
	},
	with(...e) {
		return this.check(...e);
	},
	clone(e, t) {
		return gt(this, e, t);
	},
	brand() {
		return this;
	},
	register(e, t) {
		return e.add(this, t), this;
	},
	refine(e, t) {
		return this.check(cs(e, t));
	},
	superRefine(e, t) {
		return this.check(ls(e, t));
	},
	overwrite(e) {
		return this.check(/* @__PURE__ */ $i(e));
	},
	optional() {
		return Wo(this);
	},
	exactOptional() {
		return Ko(this);
	},
	nullable() {
		return Jo(this);
	},
	nullish() {
		return Wo(Jo(this));
	},
	nonoptional(e) {
		return es(this, e);
	},
	array() {
		return R(this);
	},
	or(e) {
		return B([this, e]);
	},
	and(e) {
		return V(this, e);
	},
	transform(e) {
		return is(this, Ho(e));
	},
	default(e) {
		return Xo(this, e);
	},
	prefault(e) {
		return Qo(this, e);
	},
	catch(e) {
		return ns(this, e);
	},
	pipe(e) {
		return is(this, e);
	},
	readonly() {
		return os(this);
	},
	describe(e) {
		let t = this.clone();
		return oi.add(t, { description: e }), t;
	},
	meta(...e) {
		if (e.length === 0) return oi.get(this);
		let t = this.clone();
		return oi.add(t, e[0]), t;
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
		return oi.get(e)?.description;
	},
	configurable: !0
}), e)), io = /*@__PURE__*/ b("_ZodString", (e, t) => {
	qn.init(e, t), j.init(e, t), e._zod.processJSONSchema = (t, n, r) => ha(e, t, n, r);
	let n = e._zod.bag;
	e.format = n.format ?? null, e.minLength = n.minimum ?? null, e.maxLength = n.maximum ?? null, ro(e, "_ZodString", {
		regex(...e) {
			return this.check(/* @__PURE__ */ qi(...e));
		},
		includes(...e) {
			return this.check(/* @__PURE__ */ Xi(...e));
		},
		startsWith(...e) {
			return this.check(/* @__PURE__ */ Zi(...e));
		},
		endsWith(...e) {
			return this.check(/* @__PURE__ */ Qi(...e));
		},
		min(...e) {
			return this.check(/* @__PURE__ */ Gi(...e));
		},
		max(...e) {
			return this.check(/* @__PURE__ */ Wi(...e));
		},
		length(...e) {
			return this.check(/* @__PURE__ */ Ki(...e));
		},
		nonempty(...e) {
			return this.check(/* @__PURE__ */ Gi(1, ...e));
		},
		lowercase(e) {
			return this.check(/* @__PURE__ */ Ji(e));
		},
		uppercase(e) {
			return this.check(/* @__PURE__ */ Yi(e));
		},
		trim() {
			return this.check(/* @__PURE__ */ ta());
		},
		normalize(...e) {
			return this.check(/* @__PURE__ */ ea(...e));
		},
		toLowerCase() {
			return this.check(/* @__PURE__ */ na());
		},
		toUpperCase() {
			return this.check(/* @__PURE__ */ ra());
		},
		slugify() {
			return this.check(/* @__PURE__ */ ia());
		}
	});
}), ao = /*@__PURE__*/ b("ZodString", (e, t) => {
	qn.init(e, t), io.init(e, t), e.email = (t) => e.check(/* @__PURE__ */ ci(oo, t)), e.url = (t) => e.check(/* @__PURE__ */ mi(lo, t)), e.jwt = (t) => e.check(/* @__PURE__ */ ki(Eo, t)), e.emoji = (t) => e.check(/* @__PURE__ */ hi(fo, t)), e.guid = (t) => e.check(/* @__PURE__ */ li(so, t)), e.uuid = (t) => e.check(/* @__PURE__ */ ui(co, t)), e.uuidv4 = (t) => e.check(/* @__PURE__ */ di(co, t)), e.uuidv6 = (t) => e.check(/* @__PURE__ */ fi(co, t)), e.uuidv7 = (t) => e.check(/* @__PURE__ */ pi(co, t)), e.nanoid = (t) => e.check(/* @__PURE__ */ gi(po, t)), e.guid = (t) => e.check(/* @__PURE__ */ li(so, t)), e.cuid = (t) => e.check(/* @__PURE__ */ _i(mo, t)), e.cuid2 = (t) => e.check(/* @__PURE__ */ vi(ho, t)), e.ulid = (t) => e.check(/* @__PURE__ */ yi(go, t)), e.base64 = (t) => e.check(/* @__PURE__ */ Ei(Co, t)), e.base64url = (t) => e.check(/* @__PURE__ */ Di(wo, t)), e.xid = (t) => e.check(/* @__PURE__ */ bi(_o, t)), e.ksuid = (t) => e.check(/* @__PURE__ */ xi(vo, t)), e.ipv4 = (t) => e.check(/* @__PURE__ */ Si(yo, t)), e.ipv6 = (t) => e.check(/* @__PURE__ */ Ci(bo, t)), e.cidrv4 = (t) => e.check(/* @__PURE__ */ wi(xo, t)), e.cidrv6 = (t) => e.check(/* @__PURE__ */ Ti(So, t)), e.e164 = (t) => e.check(/* @__PURE__ */ Oi(To, t)), e.datetime = (t) => e.check(La(t)), e.date = (t) => e.check(za(t)), e.time = (t) => e.check(Va(t)), e.duration = (t) => e.check(Ua(t));
});
function M(e) {
	return /* @__PURE__ */ si(ao, e);
}
var N = /*@__PURE__*/ b("ZodStringFormat", (e, t) => {
	D.init(e, t), io.init(e, t);
}), oo = /*@__PURE__*/ b("ZodEmail", (e, t) => {
	Xn.init(e, t), N.init(e, t);
}), so = /*@__PURE__*/ b("ZodGUID", (e, t) => {
	Jn.init(e, t), N.init(e, t);
}), co = /*@__PURE__*/ b("ZodUUID", (e, t) => {
	Yn.init(e, t), N.init(e, t);
}), lo = /*@__PURE__*/ b("ZodURL", (e, t) => {
	Zn.init(e, t), N.init(e, t);
});
function uo(e) {
	return /* @__PURE__ */ mi(lo, e);
}
var fo = /*@__PURE__*/ b("ZodEmoji", (e, t) => {
	Qn.init(e, t), N.init(e, t);
}), po = /*@__PURE__*/ b("ZodNanoID", (e, t) => {
	$n.init(e, t), N.init(e, t);
}), mo = /*@__PURE__*/ b("ZodCUID", (e, t) => {
	er.init(e, t), N.init(e, t);
}), ho = /*@__PURE__*/ b("ZodCUID2", (e, t) => {
	tr.init(e, t), N.init(e, t);
}), go = /*@__PURE__*/ b("ZodULID", (e, t) => {
	nr.init(e, t), N.init(e, t);
}), _o = /*@__PURE__*/ b("ZodXID", (e, t) => {
	rr.init(e, t), N.init(e, t);
}), vo = /*@__PURE__*/ b("ZodKSUID", (e, t) => {
	ir.init(e, t), N.init(e, t);
}), yo = /*@__PURE__*/ b("ZodIPv4", (e, t) => {
	lr.init(e, t), N.init(e, t);
}), bo = /*@__PURE__*/ b("ZodIPv6", (e, t) => {
	ur.init(e, t), N.init(e, t);
}), xo = /*@__PURE__*/ b("ZodCIDRv4", (e, t) => {
	dr.init(e, t), N.init(e, t);
}), So = /*@__PURE__*/ b("ZodCIDRv6", (e, t) => {
	fr.init(e, t), N.init(e, t);
}), Co = /*@__PURE__*/ b("ZodBase64", (e, t) => {
	mr.init(e, t), N.init(e, t);
}), wo = /*@__PURE__*/ b("ZodBase64URL", (e, t) => {
	gr.init(e, t), N.init(e, t);
}), To = /*@__PURE__*/ b("ZodE164", (e, t) => {
	_r.init(e, t), N.init(e, t);
}), Eo = /*@__PURE__*/ b("ZodJWT", (e, t) => {
	yr.init(e, t), N.init(e, t);
}), Do = /*@__PURE__*/ b("ZodNumber", (e, t) => {
	br.init(e, t), j.init(e, t), e._zod.processJSONSchema = (t, n, r) => ga(e, t, n, r), ro(e, "ZodNumber", {
		gt(e, t) {
			return this.check(/* @__PURE__ */ Vi(e, t));
		},
		gte(e, t) {
			return this.check(/* @__PURE__ */ Hi(e, t));
		},
		min(e, t) {
			return this.check(/* @__PURE__ */ Hi(e, t));
		},
		lt(e, t) {
			return this.check(/* @__PURE__ */ zi(e, t));
		},
		lte(e, t) {
			return this.check(/* @__PURE__ */ Bi(e, t));
		},
		max(e, t) {
			return this.check(/* @__PURE__ */ Bi(e, t));
		},
		int(e) {
			return this.check(F(e));
		},
		safe(e) {
			return this.check(F(e));
		},
		positive(e) {
			return this.check(/* @__PURE__ */ Vi(0, e));
		},
		nonnegative(e) {
			return this.check(/* @__PURE__ */ Hi(0, e));
		},
		negative(e) {
			return this.check(/* @__PURE__ */ zi(0, e));
		},
		nonpositive(e) {
			return this.check(/* @__PURE__ */ Bi(0, e));
		},
		multipleOf(e, t) {
			return this.check(/* @__PURE__ */ Ui(e, t));
		},
		step(e, t) {
			return this.check(/* @__PURE__ */ Ui(e, t));
		},
		finite() {
			return this;
		}
	});
	let n = e._zod.bag;
	e.minValue = Math.max(n.minimum ?? -Infinity, n.exclusiveMinimum ?? -Infinity) ?? null, e.maxValue = Math.min(n.maximum ?? Infinity, n.exclusiveMaximum ?? Infinity) ?? null, e.isInt = (n.format ?? "").includes("int") || Number.isSafeInteger(n.multipleOf ?? .5), e.isFinite = !0, e.format = n.format ?? null;
});
function P(e) {
	return /* @__PURE__ */ Pi(Do, e);
}
var Oo = /*@__PURE__*/ b("ZodNumberFormat", (e, t) => {
	xr.init(e, t), Do.init(e, t);
});
function F(e) {
	return /* @__PURE__ */ Fi(Oo, e);
}
var ko = /*@__PURE__*/ b("ZodBoolean", (e, t) => {
	Sr.init(e, t), j.init(e, t), e._zod.processJSONSchema = (t, n, r) => _a(e, t, n, r);
});
function I(e) {
	return /* @__PURE__ */ Ii(ko, e);
}
var Ao = /*@__PURE__*/ b("ZodUnknown", (e, t) => {
	Cr.init(e, t), j.init(e, t), e._zod.processJSONSchema = (e, t, n) => void 0;
});
function L() {
	return /* @__PURE__ */ Li(Ao);
}
var jo = /*@__PURE__*/ b("ZodNever", (e, t) => {
	wr.init(e, t), j.init(e, t), e._zod.processJSONSchema = (t, n, r) => va(e, t, n, r);
});
function Mo(e) {
	return /* @__PURE__ */ Ri(jo, e);
}
var No = /*@__PURE__*/ b("ZodArray", (e, t) => {
	Er.init(e, t), j.init(e, t), e._zod.processJSONSchema = (t, n, r) => Ca(e, t, n, r), e.element = t.element, ro(e, "ZodArray", {
		min(e, t) {
			return this.check(/* @__PURE__ */ Gi(e, t));
		},
		nonempty(e) {
			return this.check(/* @__PURE__ */ Gi(1, e));
		},
		max(e, t) {
			return this.check(/* @__PURE__ */ Wi(e, t));
		},
		length(e, t) {
			return this.check(/* @__PURE__ */ Ki(e, t));
		},
		unwrap() {
			return this.element;
		}
	});
});
function R(e, t) {
	return /* @__PURE__ */ aa(No, e, t);
}
var Po = /*@__PURE__*/ b("ZodObject", (e, t) => {
	jr.init(e, t), j.init(e, t), e._zod.processJSONSchema = (t, n, r) => wa(e, t, n, r), S(e, "shape", () => t.shape), ro(e, "ZodObject", {
		keyof() {
			return zo(Object.keys(this._zod.def.shape));
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
				catchall: L()
			});
		},
		loose() {
			return this.clone({
				...this._zod.def,
				catchall: L()
			});
		},
		strict() {
			return this.clone({
				...this._zod.def,
				catchall: Mo()
			});
		},
		strip() {
			return this.clone({
				...this._zod.def,
				catchall: void 0
			});
		},
		extend(e) {
			return xt(this, e);
		},
		safeExtend(e) {
			return St(this, e);
		},
		merge(e) {
			return Ct(this, e);
		},
		pick(e) {
			return yt(this, e);
		},
		omit(e) {
			return bt(this, e);
		},
		partial(...e) {
			return wt(Uo, this, e[0]);
		},
		required(...e) {
			return Tt($o, this, e[0]);
		}
	});
});
function z(e, t) {
	return new Po({
		type: "object",
		shape: e ?? {},
		...C(t)
	});
}
var Fo = /*@__PURE__*/ b("ZodUnion", (e, t) => {
	Nr.init(e, t), j.init(e, t), e._zod.processJSONSchema = (t, n, r) => Ta(e, t, n, r), e.options = t.options;
});
function B(e, t) {
	return new Fo({
		type: "union",
		options: e,
		...C(t)
	});
}
var Io = /*@__PURE__*/ b("ZodIntersection", (e, t) => {
	Pr.init(e, t), j.init(e, t), e._zod.processJSONSchema = (t, n, r) => Ea(e, t, n, r);
});
function V(e, t) {
	return new Io({
		type: "intersection",
		left: e,
		right: t
	});
}
var Lo = /*@__PURE__*/ b("ZodRecord", (e, t) => {
	Lr.init(e, t), j.init(e, t), e._zod.processJSONSchema = (t, n, r) => Da(e, t, n, r), e.keyType = t.keyType, e.valueType = t.valueType;
});
function H(e, t, n) {
	return !t || !t._zod ? new Lo({
		type: "record",
		keyType: M(),
		valueType: e,
		...C(t)
	}) : new Lo({
		type: "record",
		keyType: e,
		valueType: t,
		...C(n)
	});
}
var Ro = /*@__PURE__*/ b("ZodEnum", (e, t) => {
	Rr.init(e, t), j.init(e, t), e._zod.processJSONSchema = (t, n, r) => ya(e, t, n, r), e.enum = t.entries, e.options = Object.values(t.entries);
	let n = new Set(Object.keys(t.entries));
	e.extract = (e, r) => {
		let i = {};
		for (let r of e) if (n.has(r)) i[r] = t.entries[r];
		else throw Error(`Key ${r} not found in enum`);
		return new Ro({
			...t,
			checks: [],
			...C(r),
			entries: i
		});
	}, e.exclude = (e, r) => {
		let i = { ...t.entries };
		for (let t of e) if (n.has(t)) delete i[t];
		else throw Error(`Key ${t} not found in enum`);
		return new Ro({
			...t,
			checks: [],
			...C(r),
			entries: i
		});
	};
});
function zo(e, t) {
	return new Ro({
		type: "enum",
		entries: Array.isArray(e) ? Object.fromEntries(e.map((e) => [e, e])) : e,
		...C(t)
	});
}
var Bo = /*@__PURE__*/ b("ZodLiteral", (e, t) => {
	zr.init(e, t), j.init(e, t), e._zod.processJSONSchema = (t, n, r) => ba(e, t, n, r), e.values = new Set(t.values), Object.defineProperty(e, "value", { get() {
		if (t.values.length > 1) throw Error("This schema contains multiple valid literal values. Use `.values` instead.");
		return t.values[0];
	} });
});
function U(e, t) {
	return new Bo({
		type: "literal",
		values: Array.isArray(e) ? e : [e],
		...C(t)
	});
}
var Vo = /*@__PURE__*/ b("ZodTransform", (e, t) => {
	Br.init(e, t), j.init(e, t), e._zod.processJSONSchema = (t, n, r) => Sa(e, t, n, r), e._zod.parse = (n, r) => {
		if (r.direction === "backward") throw new Xe(e.constructor.name);
		n.addIssue = (r) => {
			if (typeof r == "string") n.issues.push(jt(r, n.value, t));
			else {
				let t = r;
				t.fatal && (t.continue = !1), t.code ??= "custom", t.input ??= n.value, t.inst ??= e, n.issues.push(jt(t));
			}
		};
		let i = t.transform(n.value, n);
		return i instanceof Promise ? i.then((e) => (n.value = e, n.fallback = !0, n)) : (n.value = i, n.fallback = !0, n);
	};
});
function Ho(e) {
	return new Vo({
		type: "transform",
		transform: e
	});
}
var Uo = /*@__PURE__*/ b("ZodOptional", (e, t) => {
	Hr.init(e, t), j.init(e, t), e._zod.processJSONSchema = (t, n, r) => Fa(e, t, n, r), e.unwrap = () => e._zod.def.innerType;
});
function Wo(e) {
	return new Uo({
		type: "optional",
		innerType: e
	});
}
var Go = /*@__PURE__*/ b("ZodExactOptional", (e, t) => {
	Ur.init(e, t), j.init(e, t), e._zod.processJSONSchema = (t, n, r) => Fa(e, t, n, r), e.unwrap = () => e._zod.def.innerType;
});
function Ko(e) {
	return new Go({
		type: "optional",
		innerType: e
	});
}
var qo = /*@__PURE__*/ b("ZodNullable", (e, t) => {
	Wr.init(e, t), j.init(e, t), e._zod.processJSONSchema = (t, n, r) => Oa(e, t, n, r), e.unwrap = () => e._zod.def.innerType;
});
function Jo(e) {
	return new qo({
		type: "nullable",
		innerType: e
	});
}
var Yo = /*@__PURE__*/ b("ZodDefault", (e, t) => {
	Gr.init(e, t), j.init(e, t), e._zod.processJSONSchema = (t, n, r) => Aa(e, t, n, r), e.unwrap = () => e._zod.def.innerType, e.removeDefault = e.unwrap;
});
function Xo(e, t) {
	return new Yo({
		type: "default",
		innerType: e,
		get defaultValue() {
			return typeof t == "function" ? t() : pt(t);
		}
	});
}
var Zo = /*@__PURE__*/ b("ZodPrefault", (e, t) => {
	qr.init(e, t), j.init(e, t), e._zod.processJSONSchema = (t, n, r) => ja(e, t, n, r), e.unwrap = () => e._zod.def.innerType;
});
function Qo(e, t) {
	return new Zo({
		type: "prefault",
		innerType: e,
		get defaultValue() {
			return typeof t == "function" ? t() : pt(t);
		}
	});
}
var $o = /*@__PURE__*/ b("ZodNonOptional", (e, t) => {
	Jr.init(e, t), j.init(e, t), e._zod.processJSONSchema = (t, n, r) => ka(e, t, n, r), e.unwrap = () => e._zod.def.innerType;
});
function es(e, t) {
	return new $o({
		type: "nonoptional",
		innerType: e,
		...C(t)
	});
}
var ts = /*@__PURE__*/ b("ZodCatch", (e, t) => {
	Xr.init(e, t), j.init(e, t), e._zod.processJSONSchema = (t, n, r) => Ma(e, t, n, r), e.unwrap = () => e._zod.def.innerType, e.removeCatch = e.unwrap;
});
function ns(e, t) {
	return new ts({
		type: "catch",
		innerType: e,
		catchValue: typeof t == "function" ? t : () => t
	});
}
var rs = /*@__PURE__*/ b("ZodPipe", (e, t) => {
	Zr.init(e, t), j.init(e, t), e._zod.processJSONSchema = (t, n, r) => Na(e, t, n, r), e.in = t.in, e.out = t.out;
});
function is(e, t) {
	return new rs({
		type: "pipe",
		in: e,
		out: t
	});
}
var as = /*@__PURE__*/ b("ZodReadonly", (e, t) => {
	$r.init(e, t), j.init(e, t), e._zod.processJSONSchema = (t, n, r) => Pa(e, t, n, r), e.unwrap = () => e._zod.def.innerType;
});
function os(e) {
	return new as({
		type: "readonly",
		innerType: e
	});
}
var ss = /*@__PURE__*/ b("ZodCustom", (e, t) => {
	ti.init(e, t), j.init(e, t), e._zod.processJSONSchema = (t, n, r) => xa(e, t, n, r);
});
function cs(e, t = {}) {
	return /* @__PURE__ */ oa(ss, e, t);
}
function ls(e, t) {
	return /* @__PURE__ */ sa(e, t);
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/schema-deserialize.js
var us = Symbol("skippedItem");
function W(e, t) {
	return e.catch(t);
}
function G(e, t) {
	let n = e.catch(t);
	return L().transform((e, t) => e === void 0 ? (t.addIssue({
		code: "custom",
		message: "Required value is missing"
	}), Je) : n.parse(e));
}
function ds(e, t) {
	if (typeof e != "object" || !e || Array.isArray(e)) return;
	let n = e[t];
	return typeof n == "string" ? n : void 0;
}
function fs(e, t, n) {
	return e.superRefine((e, r) => {
		let i = ds(e, t);
		i !== void 0 && n.includes(i) && r.addIssue({
			code: "custom",
			path: [t],
			message: `${t} ${JSON.stringify(i)} is reserved by a known variant, but the value does not match that variant's schema`
		});
	});
}
function ps(e, t, n) {
	return L().transform((r, i) => {
		let a = e.safeParse(r);
		if (!a.success) {
			for (let e of a.error.issues) i.addIssue({
				...e,
				input: r
			});
			return Je;
		}
		let o = a.data, s = ds(r, t);
		if (s !== void 0 && !n.includes(s)) {
			let e = r;
			for (let [t, n] of Object.entries(e)) t !== "__proto__" && (Object.hasOwn(o, t) || (o[t] = n));
		}
		return o;
	});
}
function K(e) {
	return R(e.catch(us)).transform((e) => e.filter((e) => e !== us));
}
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/schema/zod.gen.js
var ms = B([P(), M()]).nullable(), q = M(), hs = z({
	sessionId: q,
	path: M(),
	content: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), gs = z({
	sessionId: q,
	path: M(),
	line: W(F().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	limit: W(F().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), _s = M(), vs = B([
	U("read"),
	U("edit"),
	U("delete"),
	U("move"),
	U("search"),
	U("execute"),
	U("think"),
	U("fetch"),
	U("switch_mode"),
	U("other")
]), ys = B([
	U("pending"),
	U("in_progress"),
	U("completed"),
	U("failed")
]), bs = z({
	audience: W(K(B([U("assistant"), U("user")])).nullish(), () => void 0),
	lastModified: W(M().nullish(), () => void 0),
	priority: W(P().nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), xs = z({
	annotations: W(bs.nullish(), () => void 0),
	text: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Ss = z({
	annotations: W(bs.nullish(), () => void 0),
	data: M(),
	mimeType: M(),
	uri: W(M().nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Cs = z({
	annotations: W(bs.nullish(), () => void 0),
	data: M(),
	mimeType: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), ws = z({
	annotations: W(bs.nullish(), () => void 0),
	description: W(M().nullish(), () => void 0),
	mimeType: W(M().nullish(), () => void 0),
	name: M(),
	size: W(P().nullish(), () => void 0),
	title: W(M().nullish(), () => void 0),
	uri: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Ts = B([z({
	mimeType: W(M().nullish(), () => void 0),
	text: M(),
	uri: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), z({
	blob: M(),
	mimeType: W(M().nullish(), () => void 0),
	uri: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
})]), Es = z({
	annotations: W(bs.nullish(), () => void 0),
	resource: Ts,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Ds = B([
	xs.and(z({ type: U("text") })),
	Ss.and(z({ type: U("image") })),
	Cs.and(z({ type: U("audio") })),
	ws.and(z({ type: U("resource_link") })),
	Es.and(z({ type: U("resource") }))
]), Os = z({
	content: Ds,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), ks = z({
	path: M(),
	oldText: W(M().nullish(), () => void 0),
	newText: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), As = M(), js = z({
	terminalId: As,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Ms = B([
	Os.and(z({ type: U("content") })),
	ks.and(z({ type: U("diff") })),
	js.and(z({ type: U("terminal") }))
]), Ns = z({
	path: M(),
	line: W(F().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Ps = z({
	toolCallId: _s,
	kind: W(vs.nullish(), () => void 0),
	status: W(ys.nullish(), () => void 0),
	title: W(M().nullish(), () => void 0),
	name: W(M().nullish(), () => void 0),
	content: W(K(Ms).nullish(), () => void 0),
	locations: W(K(Ns).nullish(), () => void 0),
	rawInput: W(L().optional(), () => void 0),
	rawOutput: W(L().optional(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Fs = M(), Is = B([
	U("allow_once"),
	U("allow_always"),
	U("reject_once"),
	U("reject_always")
]), Ls = z({
	sessionId: q,
	toolCall: Ps,
	options: R(z({
		optionId: Fs,
		name: M(),
		kind: Is,
		_meta: W(H(M(), L()).nullish(), () => void 0)
	})),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Rs = z({
	name: M(),
	value: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), zs = z({
	sessionId: q,
	command: M(),
	args: W(K(M()).optional(), () => []),
	env: W(K(Rs).optional(), () => []),
	cwd: W(M().nullish(), () => void 0),
	outputByteLimit: W(P().nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Bs = z({
	sessionId: q,
	terminalId: As,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Vs = z({
	sessionId: q,
	terminalId: As,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Hs = z({
	sessionId: q,
	terminalId: As,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Us = z({
	sessionId: q,
	terminalId: As,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Ws = z({
	sessionId: q,
	toolCallId: W(_s.nullish(), () => void 0)
}), Gs = z({ requestId: ms }), Ks = U("object"), qs = B([
	U("email"),
	U("uri"),
	U("date"),
	U("date-time")
]), Js = z({
	const: M(),
	title: M(),
	description: W(M().nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Ys = z({
	title: W(M().nullish(), () => void 0),
	description: W(M().nullish(), () => void 0),
	minLength: F().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(),
	maxLength: F().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(),
	pattern: M().nullish(),
	format: qs.nullish(),
	default: W(M().nullish(), () => void 0),
	enum: R(M()).nullish(),
	oneOf: R(Js).nullish(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Xs = z({
	title: W(M().nullish(), () => void 0),
	description: W(M().nullish(), () => void 0),
	minimum: P().nullish(),
	maximum: P().nullish(),
	default: W(P().nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Zs = z({
	title: W(M().nullish(), () => void 0),
	description: W(M().nullish(), () => void 0),
	minimum: P().nullish(),
	maximum: P().nullish(),
	default: W(P().nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Qs = z({
	title: W(M().nullish(), () => void 0),
	description: W(M().nullish(), () => void 0),
	default: W(I().nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), $s = z({
	enum: R(M()),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), ec = z({
	anyOf: R(Js),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), tc = ps(B([
	$s.and(z({ type: U("string") })),
	fs(z({ type: M() }), "type", ["string"]),
	ec
]), "type", ["string"]), nc = z({
	title: W(M().nullish(), () => void 0),
	description: W(M().nullish(), () => void 0),
	minItems: P().nullish(),
	maxItems: P().nullish(),
	items: tc,
	default: W(K(M()).nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), rc = ps(B([
	Ys.and(z({ type: U("string") })),
	Xs.and(z({ type: U("number") })),
	Zs.and(z({ type: U("integer") })),
	Qs.and(z({ type: U("boolean") })),
	nc.and(z({ type: U("array") })),
	fs(z({ type: M() }), "type", [
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
]), ic = z({
	type: W(Ks.optional().default("object"), () => "object"),
	title: W(M().nullish(), () => void 0),
	properties: H(M(), rc).optional().default({}),
	required: R(M()).nullish(),
	description: W(M().nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), ac = V(B([Ws, Gs]), z({ requestedSchema: ic })), oc = M(), sc = V(B([Ws, Gs]), z({
	elicitationId: oc,
	url: uo()
})), cc = ps(V(B([
	ac.and(z({ mode: U("form") })),
	sc.and(z({ mode: U("url") })),
	fs(V(B([Ws, Gs]), z({ mode: M() })), "mode", ["form", "url"])
]), z({
	message: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
})), "mode", ["form", "url"]), lc = M(), uc = z({
	serverId: lc,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), dc = M(), fc = z({
	connectionId: dc,
	method: M(),
	params: H(M(), L()).nullish(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), pc = z({
	connectionId: dc,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), mc = L();
z({
	id: ms,
	method: M(),
	params: B([
		hs,
		gs,
		Ls,
		zs,
		Bs,
		Vs,
		Hs,
		Us,
		cc,
		uc,
		fc,
		pc,
		mc
	]).nullish()
});
var hc = F().gte(0).lte(65535), gc = z({
	image: W(I().optional().default(!1), () => !1),
	audio: W(I().optional().default(!1), () => !1),
	embeddedContext: W(I().optional().default(!1), () => !1),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), _c = z({
	http: W(I().optional().default(!1), () => !1),
	sse: W(I().optional().default(!1), () => !1),
	acp: W(I().optional().default(!1), () => !1),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), vc = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), yc = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), bc = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), xc = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), Sc = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), Cc = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), wc = z({
	list: W(vc.nullish(), () => void 0),
	delete: W(yc.nullish(), () => void 0),
	additionalDirectories: W(bc.nullish(), () => void 0),
	fork: W(xc.nullish(), () => void 0),
	resume: W(Sc.nullish(), () => void 0),
	close: W(Cc.nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Tc = z({
	logout: W(z({ _meta: W(H(M(), L()).nullish(), () => void 0) }).nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Ec = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), Dc = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), Oc = z({
	syncKind: B([U("full"), U("incremental")]),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), kc = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), Ac = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), jc = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), Mc = z({
	document: W(z({
		didOpen: W(Dc.nullish(), () => void 0),
		didChange: W(Oc.nullish(), () => void 0),
		didClose: W(kc.nullish(), () => void 0),
		didSave: W(Ac.nullish(), () => void 0),
		didFocus: W(jc.nullish(), () => void 0),
		_meta: W(H(M(), L()).nullish(), () => void 0)
	}).nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Nc = z({
	maxCount: W(F().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Pc = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), Fc = z({
	maxCount: W(F().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Ic = z({
	maxCount: W(F().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Lc = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), Rc = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), zc = z({
	recentFiles: W(Nc.nullish(), () => void 0),
	relatedSnippets: W(Pc.nullish(), () => void 0),
	editHistory: W(Fc.nullish(), () => void 0),
	userActions: W(Ic.nullish(), () => void 0),
	openFiles: W(Lc.nullish(), () => void 0),
	diagnostics: W(Rc.nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Bc = z({
	events: W(Mc.nullish(), () => void 0),
	context: W(zc.nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Vc = B([
	U("utf-16"),
	U("utf-32"),
	U("utf-8")
]), Hc = z({
	loadSession: W(I().optional().default(!1), () => !1),
	promptCapabilities: W(gc.optional().default({
		image: !1,
		audio: !1,
		embeddedContext: !1
	}), () => ({
		image: !1,
		audio: !1,
		embeddedContext: !1
	})),
	mcpCapabilities: W(_c.optional().default({
		http: !1,
		sse: !1,
		acp: !1
	}), () => ({
		http: !1,
		sse: !1,
		acp: !1
	})),
	sessionCapabilities: W(wc.optional().default({}), () => ({})),
	auth: W(Tc.optional().default({}), () => ({})),
	providers: W(Ec.nullish(), () => void 0),
	nes: W(Bc.nullish(), () => void 0),
	positionEncoding: W(Vc.nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Uc = M(), Wc = z({
	id: Uc,
	name: M(),
	description: W(M().nullish(), () => void 0),
	args: W(K(M()).optional(), () => []),
	env: W(H(M(), M()).optional(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Gc = z({
	id: Uc,
	name: M(),
	description: W(M().nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Kc = B([Wc.and(z({ type: U("terminal") })), Gc]), qc = z({
	name: M(),
	title: W(M().nullish(), () => void 0),
	version: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Jc = z({
	protocolVersion: hc,
	agentCapabilities: W(Hc.optional().default({
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
	authMethods: W(K(Kc).optional().default([]), () => []),
	agentInfo: W(qc.nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Yc = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), Xc = M(), Zc = B([
	U("anthropic"),
	U("openai"),
	U("azure"),
	U("vertex"),
	U("bedrock"),
	M()
]), Qc = z({
	apiType: Zc,
	baseUrl: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), $c = z({
	providers: R(z({
		providerId: Xc,
		supported: G(K(Zc), () => []),
		required: I(),
		current: Qc.nullish(),
		_meta: W(H(M(), L()).nullish(), () => void 0)
	})),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), el = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), tl = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), nl = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), rl = M(), il = z({
	currentModeId: rl,
	availableModes: G(K(z({
		id: rl,
		name: M(),
		description: W(M().nullish(), () => void 0),
		_meta: W(H(M(), L()).nullish(), () => void 0)
	})), () => []),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), al = M(), ol = B([
	U("mode"),
	U("model"),
	U("model_config"),
	U("thought_level"),
	M()
]), sl = M(), cl = z({
	value: sl,
	name: M(),
	description: W(M().nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), ll = z({
	group: M(),
	name: M(),
	options: G(K(cl), () => []),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), ul = z({
	currentValue: sl,
	options: B([R(cl), R(ll)])
}), dl = z({ currentValue: I() }), fl = V(B([ul.and(z({ type: U("select") })), dl.and(z({ type: U("boolean") }))]), z({
	id: al,
	name: M(),
	description: W(M().nullish(), () => void 0),
	category: W(ol.nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
})), pl = z({
	sessionId: q,
	modes: W(il.nullish(), () => void 0),
	configOptions: W(K(fl).nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), ml = z({
	modes: W(il.nullish(), () => void 0),
	configOptions: W(K(fl).nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), hl = z({
	sessions: G(K(z({
		sessionId: q,
		cwd: M(),
		additionalDirectories: W(K(M()).optional(), () => []),
		title: W(M().nullish(), () => void 0),
		updatedAt: W(M().nullish(), () => void 0),
		_meta: W(H(M(), L()).nullish(), () => void 0)
	})), () => []),
	nextCursor: W(M().nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), gl = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), _l = z({
	sessionId: q,
	modes: W(il.nullish(), () => void 0),
	configOptions: W(K(fl).nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), vl = z({
	modes: W(il.nullish(), () => void 0),
	configOptions: W(K(fl).nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), yl = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), bl = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), xl = z({
	configOptions: G(K(fl), () => []),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Sl = z({
	stopReason: B([
		U("end_turn"),
		U("max_tokens"),
		U("max_turn_requests"),
		U("refusal"),
		U("cancelled")
	]),
	usage: W(z({
		totalTokens: P(),
		inputTokens: P(),
		outputTokens: P(),
		thoughtTokens: W(P().nullish(), () => void 0),
		cachedReadTokens: W(P().nullish(), () => void 0),
		cachedWriteTokens: W(P().nullish(), () => void 0),
		_meta: W(H(M(), L()).nullish(), () => void 0)
	}).nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Cl = z({
	sessionId: q,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), wl = M(), Tl = z({
	line: F().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }),
	character: F().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), El = z({
	start: Tl,
	end: Tl,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Dl = z({
	range: El,
	newText: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Ol = z({
	id: wl,
	uri: M(),
	edits: R(Dl),
	cursorPosition: W(Tl.nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), kl = z({
	id: wl,
	uri: M(),
	position: Tl,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Al = z({
	id: wl,
	uri: M(),
	position: Tl,
	newName: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), jl = z({
	id: wl,
	uri: M(),
	search: M(),
	replace: M(),
	isRegex: I().nullish(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Ml = z({
	suggestions: R(B([
		Ol.and(z({ kind: U("edit") })),
		kl.and(z({ kind: U("jump") })),
		Al.and(z({ kind: U("rename") })),
		jl.and(z({ kind: U("searchAndReplace") }))
	])),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Nl = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), Pl = L(), Fl = L(), Il = z({
	code: B([
		U(-32700),
		U(-32600),
		U(-32601),
		U(-32602),
		U(-32603),
		U(-32800),
		U(-32e3),
		U(-32002),
		F().min(-2147483648, { error: "Invalid value: Expected int32 to be >= -2147483648" }).max(2147483647, { error: "Invalid value: Expected int32 to be <= 2147483647" })
	]),
	message: M(),
	data: W(L().optional(), () => void 0)
});
B([z({
	id: ms,
	result: B([
		Jc,
		Yc,
		$c,
		el,
		tl,
		nl,
		pl,
		ml,
		hl,
		gl,
		_l,
		vl,
		yl,
		bl,
		xl,
		Sl,
		Cl,
		Ml,
		Nl,
		Pl,
		Fl
	])
}), z({
	id: ms,
	error: Il
})]);
var Ll = z({
	content: Ds,
	messageId: W(M().nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Rl = z({
	toolCallId: _s,
	title: M(),
	name: W(M().nullish(), () => void 0),
	kind: W(vs.optional(), () => void 0),
	status: W(ys.optional(), () => void 0),
	content: W(K(Ms).optional(), () => []),
	locations: W(K(Ns).optional(), () => []),
	rawInput: W(L().optional(), () => void 0),
	rawOutput: W(L().optional(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), zl = B([
	U("high"),
	U("medium"),
	U("low")
]), Bl = B([
	U("pending"),
	U("in_progress"),
	U("completed")
]), Vl = z({
	content: M(),
	priority: zl,
	status: Bl,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Hl = z({
	entries: G(K(Vl), () => []),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Ul = M(), Wl = z({
	planId: Ul,
	entries: G(K(Vl), () => []),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Gl = z({
	planId: Ul,
	uri: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Kl = z({
	planId: Ul,
	content: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), ql = z({
	plan: B([
		Wl.and(z({ type: U("items") })),
		Gl.and(z({ type: U("file") })),
		Kl.and(z({ type: U("markdown") }))
	]),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Jl = z({
	planId: Ul,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Yl = z({
	hint: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Xl = z({
	availableCommands: G(K(z({
		name: M(),
		description: M(),
		input: W(Yl.nullish(), () => void 0),
		_meta: W(H(M(), L()).nullish(), () => void 0)
	})), () => []),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Zl = z({
	currentModeId: rl,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Ql = z({
	configOptions: G(K(fl), () => []),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), $l = z({
	title: W(M().nullish(), () => void 0),
	updatedAt: W(M().nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), eu = z({
	amount: P(),
	currency: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), tu = z({
	used: P(),
	size: P(),
	cost: W(eu.nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), nu = M(), ru = z({
	compactionId: nu,
	status: B([
		U("in_progress"),
		U("completed"),
		U("failed"),
		U("cancelled"),
		M()
	]),
	summary: W(K(Ds).nullish(), () => void 0),
	error: W(M().nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), iu = z({
	compactionId: nu,
	content: Ds,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), au = z({
	sessionId: q,
	update: B([
		Ll.and(z({ sessionUpdate: U("user_message_chunk") })),
		Ll.and(z({ sessionUpdate: U("agent_message_chunk") })),
		Ll.and(z({ sessionUpdate: U("agent_thought_chunk") })),
		Rl.and(z({ sessionUpdate: U("tool_call") })),
		Ps.and(z({ sessionUpdate: U("tool_call_update") })),
		Hl.and(z({ sessionUpdate: U("plan") })),
		ql.and(z({ sessionUpdate: U("plan_update") })),
		Jl.and(z({ sessionUpdate: U("plan_removed") })),
		Xl.and(z({ sessionUpdate: U("available_commands_update") })),
		Zl.and(z({ sessionUpdate: U("current_mode_update") })),
		Ql.and(z({ sessionUpdate: U("config_option_update") })),
		$l.and(z({ sessionUpdate: U("session_info_update") })),
		tu.and(z({ sessionUpdate: U("usage_update") })),
		ru.and(z({ sessionUpdate: U("compaction_update") })),
		iu.and(z({ sessionUpdate: U("compaction_summary_chunk") }))
	]),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), ou = z({
	elicitationId: oc,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), su = z({
	connectionId: dc,
	method: M(),
	params: W(H(M(), L()).nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), cu = L();
z({
	method: M(),
	params: B([
		au,
		ou,
		su,
		cu
	]).nullish()
});
var lu = z({
	readTextFile: W(I().optional().default(!1), () => !1),
	writeTextFile: W(I().optional().default(!1), () => !1),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), uu = H(M(), L()), du = z({
	boolean: W(z({ _meta: W(H(M(), L()).nullish(), () => void 0) }).nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), fu = z({
	compaction: W(uu.nullish(), () => void 0),
	configOptions: W(du.nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), pu = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), mu = z({
	terminal: W(I().optional().default(!1), () => !1),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), hu = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), gu = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), _u = z({
	form: W(hu.nullish(), () => void 0),
	url: W(gu.nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), vu = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), yu = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), bu = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), xu = z({
	jump: W(vu.nullish(), () => void 0),
	rename: W(yu.nullish(), () => void 0),
	searchAndReplace: W(bu.nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Su = z({
	protocolVersion: hc,
	clientCapabilities: W(z({
		fs: W(lu.optional().default({
			readTextFile: !1,
			writeTextFile: !1
		}), () => ({
			readTextFile: !1,
			writeTextFile: !1
		})),
		terminal: W(I().optional().default(!1), () => !1),
		session: W(fu.nullish(), () => void 0),
		plan: W(pu.nullish(), () => void 0),
		auth: W(mu.optional().default({ terminal: !1 }), () => ({ terminal: !1 })),
		elicitation: W(_u.nullish(), () => void 0),
		nes: W(xu.nullish(), () => void 0),
		positionEncodings: W(K(Vc).optional(), () => []),
		_meta: W(H(M(), L()).nullish(), () => void 0)
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
	clientInfo: W(qc.nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Cu = z({
	methodId: Uc,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), wu = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), Tu = z({
	providerId: Xc,
	apiType: Zc,
	baseUrl: M(),
	headers: H(M(), M()).optional(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Eu = z({
	providerId: Xc,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Du = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), Ou = z({
	name: M(),
	value: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), ku = z({
	name: M(),
	url: M(),
	headers: R(Ou),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Au = z({
	name: M(),
	url: M(),
	headers: R(Ou),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), ju = z({
	name: M(),
	serverId: lc,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Mu = z({
	name: M(),
	command: M(),
	args: R(M()),
	env: R(Rs),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Nu = B([
	ku.and(z({ type: U("http") })),
	Au.and(z({ type: U("sse") })),
	ju.and(z({ type: U("acp") })),
	Mu
]), Pu = z({
	cwd: M(),
	additionalDirectories: W(K(M()).optional(), () => []),
	mcpServers: G(K(Nu), () => []),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Fu = z({
	mcpServers: G(K(Nu), () => []),
	cwd: M(),
	additionalDirectories: W(K(M()).optional(), () => []),
	sessionId: q,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Iu = z({
	cwd: M().nullish(),
	cursor: M().nullish(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Lu = z({
	sessionId: q,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Ru = z({
	sessionId: q,
	cwd: M(),
	additionalDirectories: W(K(M()).optional(), () => []),
	mcpServers: W(K(Nu).optional(), () => []),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), zu = z({
	sessionId: q,
	cwd: M(),
	additionalDirectories: W(K(M()).optional(), () => []),
	mcpServers: W(K(Nu).optional(), () => []),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Bu = z({
	sessionId: q,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Vu = z({
	sessionId: q,
	modeId: rl,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Hu = V(B([z({
	value: I(),
	type: U("boolean")
}), z({ value: sl })]), z({
	sessionId: q,
	configId: al,
	_meta: W(H(M(), L()).nullish(), () => void 0)
})), Uu = z({
	sessionId: q,
	prompt: R(Ds),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Wu = z({
	uri: M(),
	name: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Gu = z({
	name: M(),
	owner: M(),
	remoteUrl: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Ku = z({
	workspaceUri: W(M().nullish(), () => void 0),
	workspaceFolders: R(Wu).nullish(),
	repository: W(Gu.nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), qu = B([
	U("automatic"),
	U("diagnostic"),
	U("manual")
]), Ju = z({
	uri: M(),
	languageId: M(),
	text: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Yu = z({
	startLine: F().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }),
	endLine: F().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }),
	text: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Xu = z({
	uri: M(),
	excerpts: R(Yu),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Zu = z({
	uri: M(),
	diff: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Qu = z({
	action: M(),
	uri: M(),
	position: Tl,
	timestampMs: P(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), $u = z({
	uri: M(),
	languageId: M(),
	visibleRange: W(El.nullish(), () => void 0),
	lastFocusedMs: W(P().nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), ed = B([
	U("error"),
	U("warning"),
	U("information"),
	U("hint")
]), td = z({
	uri: M(),
	range: El,
	severity: ed,
	message: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), nd = z({
	recentFiles: R(Ju).nullish(),
	relatedSnippets: R(Xu).nullish(),
	editHistory: R(Zu).nullish(),
	userActions: R(Qu).nullish(),
	openFiles: R($u).nullish(),
	diagnostics: R(td).nullish(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), rd = z({
	sessionId: q,
	uri: M(),
	version: P(),
	position: Tl,
	selection: El.nullish(),
	triggerKind: qu,
	context: nd.nullish(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), id = z({
	sessionId: q,
	_meta: W(H(M(), L()).nullish(), () => void 0)
});
z({
	id: ms,
	method: M(),
	params: B([
		Su,
		Cu,
		wu,
		Tu,
		Eu,
		Du,
		Pu,
		Fu,
		Iu,
		Lu,
		Ru,
		zu,
		Bu,
		Vu,
		Hu,
		Uu,
		Ku,
		rd,
		id,
		fc,
		mc
	]).nullish()
});
var ad = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), od = z({
	content: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), sd = z({
	optionId: Fs,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), cd = z({
	outcome: B([z({ outcome: U("cancelled") }), sd.and(z({ outcome: U("selected") }))]),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), ld = z({
	terminalId: As,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), ud = z({
	exitCode: W(F().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	signal: W(M().nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), dd = z({
	output: M(),
	truncated: I(),
	exitStatus: W(ud.nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), fd = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), pd = z({
	exitCode: W(F().gte(0).max(4294967295, { error: "Invalid value: Expected uint32 to be <= 4294967295" }).nullish(), () => void 0),
	signal: W(M().nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), md = z({ _meta: W(H(M(), L()).nullish(), () => void 0) }), hd = B([
	M(),
	P(),
	P(),
	I(),
	R(M())
]), gd = z({ content: H(M(), hd).nullish() });
B([z({
	id: ms,
	result: B([
		ad,
		od,
		cd,
		ld,
		dd,
		fd,
		pd,
		md,
		ps(V(B([
			gd.and(z({ action: U("accept") })),
			z({ action: U("decline") }),
			z({ action: U("cancel") }),
			fs(z({ action: M() }), "action", [
				"accept",
				"cancel",
				"decline"
			])
		]), z({ _meta: W(H(M(), L()).nullish(), () => void 0) })), "action", [
			"accept",
			"cancel",
			"decline"
		]),
		z({
			connectionId: dc,
			_meta: W(H(M(), L()).nullish(), () => void 0)
		}),
		z({ _meta: W(H(M(), L()).nullish(), () => void 0) }),
		Fl,
		Pl
	])
}), z({
	id: ms,
	error: Il
})]);
var _d = z({
	sessionId: q,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), vd = z({
	sessionId: q,
	uri: M(),
	languageId: M(),
	version: P(),
	text: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), yd = z({
	range: El.nullish(),
	text: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), bd = z({
	sessionId: q,
	uri: M(),
	version: P(),
	contentChanges: G(K(yd), () => []),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), xd = z({
	sessionId: q,
	uri: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Sd = z({
	sessionId: q,
	uri: M(),
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Cd = z({
	sessionId: q,
	uri: M(),
	version: P(),
	position: Tl,
	visibleRange: El,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), wd = z({
	sessionId: q,
	id: wl,
	_meta: W(H(M(), L()).nullish(), () => void 0)
}), Td = z({
	sessionId: q,
	id: wl,
	reason: W(B([
		U("rejected"),
		U("ignored"),
		U("replaced"),
		U("cancelled")
	]).nullish(), () => void 0),
	_meta: W(H(M(), L()).nullish(), () => void 0)
});
z({
	method: M(),
	params: B([
		_d,
		vd,
		bd,
		xd,
		Sd,
		Cd,
		wd,
		Td,
		su,
		cu
	]).nullish()
}), z({
	requestId: ms,
	_meta: W(H(M(), L()).nullish(), () => void 0)
});
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/jsonrpc.js
var Ed = "$/cancel_request";
function Dd(e) {
	return jd(e) && "id" in e && typeof e.method == "string" && Md(e.id);
}
function Od(e) {
	if (!jd(e) || "method" in e || !("id" in e) || !Md(e.id)) return !1;
	let t = Object.hasOwn(e, "result"), n = Object.hasOwn(e, "error");
	return t === n ? !1 : !n || Id(e.error);
}
function kd(e) {
	return jd(e) && !("id" in e) && typeof e.method == "string";
}
function Ad(e) {
	return typeof e == "object" && !!e;
}
function jd(e) {
	return Ad(e) && e.jsonrpc === "2.0";
}
function Md(e) {
	return e === null || typeof e == "string" || typeof e == "number" && Number.isFinite(e);
}
function Nd(e) {
	return Ad(e) && !("method" in e) && ("id" in e || "result" in e || "error" in e);
}
function Pd(e) {
	let t = !1, n = !1, r = !1, i = !1;
	for (let a of e) t ||= Dd(a) || kd(a), n ||= Od(a), Ad(a) && (r ||= "method" in a, i ||= "result" in a || "error" in a);
	return t ? !1 : n ? !0 : i && !r;
}
function Fd(e) {
	if (!(!Ad(e) || !Md(e.requestId))) return e.requestId;
}
function Id(e) {
	return Ad(e) && typeof e.code == "number" && Number.isInteger(e.code) && typeof e.message == "string";
}
var J = {
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
function Ld(e) {
	let t = Promise.reject(e);
	return t.catch(() => {}), t;
}
function Rd(e) {
	if (e instanceof Error || typeof e == "object" && e && "message" in e && typeof e.message == "string") return e.message;
}
function zd(e) {
	return typeof e == "object" && !!e && "name" in e && e.name === "ZodError" && "issues" in e && Array.isArray(e.issues) && "format" in e && typeof e.format == "function";
}
function Bd(e) {
	if (e instanceof Y) return e.toResult();
	if (zd(e)) return Y.invalidParams(e.format()).toResult();
	let t = Rd(e);
	try {
		return Y.internalError(t ? JSON.parse(t) : {}).toResult();
	} catch {
		return Y.internalError({ details: t }).toResult();
	}
}
function Vd(e) {
	return e instanceof Y && e.code === -32800 ? e : Y.requestCancelled(e);
}
function Hd(e, t) {
	let n = Ud(e, t);
	return n ? n.toResult() : Bd(e);
}
function Ud(e, t) {
	if (!(!t.aborted || !Wd(e))) return Vd(t.reason);
}
function Wd(e) {
	if (typeof e != "object" || !e) return !1;
	let t = e;
	return t.name === "AbortError" || t.code === "ABORT_ERR";
}
var Gd = class {
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
		let t = e instanceof Y ? e.toErrorResponse() : e;
		return this.respondWithResult({ error: t });
	}
	respondWithResult(e) {
		return this.didRespond ? Ld(/* @__PURE__ */ Error("JSON-RPC request already responded")) : (this.didRespond = !0, this.sendResult(e).finally(() => {
			this.finishRequest?.();
		}));
	}
}, Kd = /* @__PURE__ */ new WeakMap(), qd = class {
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
}, Jd = class {
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
}, Yd = class {
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
	context = new Jd(this);
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
		return new Xd();
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
		return new qd(() => {
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
		if (this.abortController.signal.aborted) return Ld(this.closedReason());
		let i = this.prepareRequest(e, t, n, r);
		return this.sendWireMessage(i.message).catch(() => {}), r.cancellationSignal?.aborted && i.cancel(), i.response;
	}
	sendBatch(e) {
		if (this.abortController.signal.aborted) return Ld(this.closedReason());
		if (!this.allowBatches) return Ld(/* @__PURE__ */ TypeError("JSON-RPC batches are not supported on this connection"));
		if (e.length === 0) return Ld(/* @__PURE__ */ TypeError("JSON-RPC batch must contain at least one entry"));
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
		return this.sendNotification(Ed, { requestId: e });
	}
	sendNotification(e, t) {
		return this.abortController.signal.aborted ? Ld(this.closedReason()) : this.sendWireMessage({
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
			return J.yes();
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
		if (!Dd(e) && !kd(e) && !Nd(e)) {
			this.sendWireMessage(Zd(Y.invalidRequest(e))).catch(() => {});
			return;
		}
		this.receiveMessage(e);
	}
	receiveBatch(e) {
		if (e.length === 0) {
			this.sendWireMessage(Zd(Y.invalidRequest(e))).catch(() => {});
			return;
		}
		let t = Pd(e), n = t ? 0 : e.reduce((e, t) => e + +!kd(t), 0), r = e.reduce((e, t) => e + +!!kd(t), 0), i = !1, a = [], o = async () => {
			i || n !== 0 || r !== 0 || a.length === 0 || (i = !0, await this.sendWireMessage(a));
		}, s = async (e) => {
			a.push(e), --n, await o();
		};
		for (let n of e) {
			if (t) {
				Nd(n) && this.receiveMessage(n);
				continue;
			}
			if (!Dd(n) && !kd(n)) {
				s(Zd(Y.invalidRequest(n))).catch(() => {});
				continue;
			}
			let i = this.receiveMessage(n, Dd(n) ? s : void 0, e.length);
			kd(n) && i.finally(() => {
				--r, o().catch((e) => this.close(e));
			});
		}
	}
	receiveMessage(e, t, n) {
		return this.abortController.signal.aborted ? Promise.resolve() : Ad(e) ? "method" in e ? ("id" in e || this.handleProtocolNotification(e), this.processIncomingMessage(this.toIncomingMessage(e, t, n)).catch((e) => this.close(e))) : ("id" in e ? this.handleResponse(e) : console.error("Invalid message", { message: e }), Promise.resolve()) : (console.error("Invalid message", { message: e }), Promise.resolve());
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
			n ? this.retryQueue.push(t) : t.kind === "request" && await t.responder.respondWithError(Y.methodNotFound(t.method));
		} catch (n) {
			if (this.abortController.signal.aborted) return;
			if (t.kind === "request" && !t.responder.responded) await t.responder.respondWithResult(Hd(n, t.responder.signal));
			else {
				let t = Bd(n);
				"error" in t && console.error("Error handling notification", e.raw, t.error);
			}
		}
	}
	toIncomingMessage(e, t, n) {
		if ("id" in e) {
			let r = new AbortController();
			this.incomingRequests.set(e.id, r);
			let i = new Gd(e.id, (n) => {
				let r = {
					jsonrpc: "2.0",
					id: e.id,
					...n
				};
				return t ? t(r) : this.sendWireMessage(r);
			}, r.signal, () => {
				this.incomingRequests.get(e.id) === r && this.incomingRequests.delete(e.id);
			});
			return n !== void 0 && Kd.set(i, n), {
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
			if (this.pendingResponses.delete(e.id), t.cleanup?.(), !Od(e)) t.reject(Y.invalidRequest(e));
			else if ("result" in e) t.resolve(e.result);
			else {
				let { code: n, message: r, data: i } = e.error;
				t.reject(new Y(n, r, i));
			}
		} else console.error("Got response to unknown request", e.id);
	}
	handleProtocolNotification(e) {
		if (e.method !== Ed) return;
		let t = Fd(e.params);
		if (t === void 0) return;
		let n = this.incomingRequests.get(t);
		!n || n.signal.aborted || n.abort(Y.requestCancelled({ requestId: t }));
	}
	closedReason() {
		return this.abortController.signal.reason ?? /* @__PURE__ */ Error("ACP connection closed");
	}
	async sendWireMessage(e) {
		return this.abortController.signal.aborted ? Ld(this.closedReason()) : (this.writeQueue = this.writeQueue.then(async () => {
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
}, Xd = class {
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
			handleMessage: async (t, n) => await e(t, n) ?? J.no(t),
			describe: () => this.connectionName ?? "onReceiveMessage"
		});
	}
	onReceiveRequest(e, t, n) {
		return this.withHandler({
			handleMessage: async (r, i) => r.kind !== "request" || r.method !== e ? J.no(r) : await n(t(r.params), r.responder, i) ?? J.yes(),
			describe: () => `${this.connectionName ?? "request"}:${e}`
		});
	}
	onReceiveNotification(e, t, n) {
		return this.withHandler({
			handleMessage: async (r, i) => r.kind !== "notification" || r.method !== e ? J.no(r) : await n(t(r.params), i) ?? J.yes(),
			describe: () => `${this.connectionName ?? "notification"}:${e}`
		});
	}
	connect(e, t) {
		return new Yd(e, this.handlers, t);
	}
	connectWith(e, t, n) {
		return this.connect(e, n).runUntil(t);
	}
}, Y = class e extends Error {
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
function Zd(e) {
	return {
		jsonrpc: "2.0",
		id: null,
		error: e.toErrorResponse()
	};
}
ac.and(z({ mode: U("form") })).and(z({ message: M() })), sc.and(z({ mode: U("url") })).and(z({ message: M() })), B([Ws, Gs]).and(z({ message: M() })), Ys.and(z({ type: U("string") })), Xs.and(z({ type: U("number") })), Zs.and(z({ type: U("integer") })), Qs.and(z({ type: U("boolean") })), nc.and(z({ type: U("array") })), $s.and(z({ type: U("string") })), gd.and(z({ action: U("accept") })), z({ action: U("decline") }), z({ action: U("cancel") });
//#endregion
//#region node_modules/.pnpm/@agentclientprotocol+sdk@1.4.0_zod@4.4.3/node_modules/@agentclientprotocol/sdk/dist/acp.js
function X(e) {
	return e ?? {};
}
function Qd(e) {
	return typeof e == "object" && !!e && "readable" in e && "writable" in e;
}
function $d() {
	let e = new TransformStream(), t = new TransformStream();
	return [{
		readable: t.readable,
		writable: e.writable
	}, {
		readable: e.readable,
		writable: t.writable
	}];
}
var ef = {
	agent: {
		initialize: v.initialize,
		authenticate: v.authenticate,
		logout: v.logout,
		providers: {
			list: v.providers_list,
			set: v.providers_set,
			disable: v.providers_disable
		},
		session: {
			new: v.session_new,
			load: v.session_load,
			list: v.session_list,
			delete: v.session_delete,
			fork: v.session_fork,
			resume: v.session_resume,
			close: v.session_close,
			setMode: v.session_set_mode,
			setConfigOption: v.session_set_config_option,
			prompt: v.session_prompt,
			cancel: v.session_cancel
		},
		nes: {
			start: v.nes_start,
			suggest: v.nes_suggest,
			accept: v.nes_accept,
			reject: v.nes_reject,
			close: v.nes_close
		},
		document: {
			didOpen: v.document_did_open,
			didChange: v.document_did_change,
			didClose: v.document_did_close,
			didSave: v.document_did_save,
			didFocus: v.document_did_focus
		}
	},
	client: {
		session: {
			requestPermission: y.session_request_permission,
			update: y.session_update
		},
		fs: {
			writeTextFile: y.fs_write_text_file,
			readTextFile: y.fs_read_text_file
		},
		terminal: {
			create: y.terminal_create,
			output: y.terminal_output,
			release: y.terminal_release,
			waitForExit: y.terminal_wait_for_exit,
			kill: y.terminal_kill
		},
		elicitation: {
			create: y.elicitation_create,
			complete: y.elicitation_complete
		}
	},
	protocol: { cancelRequest: Ke.cancel_request }
}, tf = Symbol("startActiveSession"), nf = class {
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
}, rf = class e extends nf {
	constructor(e, t) {
		super(e, t);
	}
	static create(t, n) {
		return new e(t, n);
	}
	request(e, t, n) {
		let r = wf[e];
		return this.sendRequest(e, t, r?.mapResponse, n);
	}
	notify(e, t) {
		return this.sendNotification(e, t);
	}
}, af = class e extends nf {
	constructor(e, t) {
		super(e, t);
	}
	static create(t, n) {
		return new e(t, n);
	}
	[tf](e, t) {
		return this.sendRequest(v.session_new, e, (e) => this.attachSession(e), t);
	}
	buildSession(e) {
		return typeof e == "string" ? pf.create(this, {
			cwd: e,
			mcpServers: []
		}) : pf.create(this, e);
	}
	attachSession(e) {
		let t = new df(), n = this.connectionContext.signal, r = () => {
			t.fail(n.reason ?? /* @__PURE__ */ Error("ACP connection closed"));
		};
		n.aborted ? r() : n.addEventListener("abort", r);
		let i = Af(this.connectionContext).attach(e, t), a = new qd(() => {
			n.removeEventListener("abort", r);
		});
		return mf.create(this, e, t, [i, a]);
	}
	request(e, t, n) {
		let r = Cf[e];
		return this.sendRequest(e, t, r?.mapResponse, n);
	}
	notify(e, t) {
		return this.sendNotification(e, t);
	}
}, of = class {
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
}, sf = class extends of {
	connectHandlers;
	client;
	didStartConnectHandlers = !1;
	constructor(e, t = []) {
		super(e), this.connectHandlers = t, this.client = rf.create(e.getContext());
	}
	startConnectHandlers() {
		this.didStartConnectHandlers || (this.didStartConnectHandlers = !0, jf(this, this.connectHandlers));
	}
}, cf = class extends of {
	connectHandlers;
	agent;
	didStartConnectHandlers = !1;
	constructor(e, t = []) {
		super(e), this.connectHandlers = t, this.agent = af.create(e.getContext());
	}
	startConnectHandlers() {
		this.didStartConnectHandlers || (this.didStartConnectHandlers = !0, jf(this, this.connectHandlers));
	}
};
function lf(e, t = []) {
	return new sf(e, t);
}
function uf(e, t = []) {
	return new cf(e, t);
}
var df = class {
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
function ff(e) {
	return {
		...e,
		additionalDirectories: e.additionalDirectories ? [...e.additionalDirectories] : void 0,
		mcpServers: [...e.mcpServers]
	};
}
var pf = class e {
	cx;
	request;
	constructor(e, t) {
		this.cx = e, this.request = ff(t);
	}
	static create(t, n) {
		return new e(t, n);
	}
	toRequest() {
		return ff(this.request);
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
		return this.cx[tf](this.toRequest(), e);
	}
	async withSession(e) {
		let t = await this.start();
		try {
			return await e(t);
		} finally {
			t.dispose();
		}
	}
}, mf = class e {
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
		let n = this.cx.request(v.session_prompt, {
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
function hf(e, t) {
	return e ? typeof e == "function" ? e(t) : e.parse(t) : t;
}
function Z(e, t, n) {
	return {
		method: e,
		params: t,
		mapResponse: n
	};
}
function Q(e, t) {
	return {
		method: e,
		params: t
	};
}
function gf(e, t, n, r) {
	e.onReceiveRequest(t.method, (e) => hf(t.params, e), async (e, i, a) => {
		let o = await r(n(e, a, i.signal, i.id));
		await i.respond(t.mapResponse ? t.mapResponse(o) : o);
	});
}
function _f(e, t, n, r) {
	e.onReceiveNotification(t.method, (e) => hf(t.params, e), (e, t) => r(n(e, t, t.signal)));
}
function vf(e) {
	let t = {};
	for (let n of Object.values(e)) t[n.method] = n;
	return t;
}
var yf = {
	initialize: Z(v.initialize, Su),
	newSession: Z(v.session_new, Pu),
	loadSession: Z(v.session_load, Fu, X),
	unstable_forkSession: Z(v.session_fork, Ru),
	listSessions: Z(v.session_list, Iu),
	deleteSession: Z(v.session_delete, Lu, X),
	resumeSession: Z(v.session_resume, zu),
	closeSession: Z(v.session_close, Bu, X),
	setSessionMode: Z(v.session_set_mode, Vu, X),
	setSessionConfigOption: Z(v.session_set_config_option, Hu),
	authenticate: Z(v.authenticate, Cu, X),
	unstable_listProviders: Z(v.providers_list, wu),
	unstable_setProvider: Z(v.providers_set, Tu, X),
	unstable_disableProvider: Z(v.providers_disable, Eu, X),
	logout: Z(v.logout, Du, X),
	prompt: Z(v.session_prompt, Uu),
	unstable_startNes: Z(v.nes_start, Ku),
	unstable_suggestNes: Z(v.nes_suggest, rd),
	unstable_closeNes: Z(v.nes_close, id, X)
}, bf = {
	cancel: Q(v.session_cancel, _d),
	unstable_didOpenDocument: Q(v.document_did_open, vd),
	unstable_didChangeDocument: Q(v.document_did_change, bd),
	unstable_didCloseDocument: Q(v.document_did_close, xd),
	unstable_didSaveDocument: Q(v.document_did_save, Sd),
	unstable_didFocusDocument: Q(v.document_did_focus, Cd),
	unstable_acceptNes: Q(v.nes_accept, wd),
	unstable_rejectNes: Q(v.nes_reject, Td)
}, xf = {
	requestPermission: Z(y.session_request_permission, Ls),
	writeTextFile: Z(y.fs_write_text_file, hs, X),
	readTextFile: Z(y.fs_read_text_file, gs),
	createTerminal: Z(y.terminal_create, zs),
	terminalOutput: Z(y.terminal_output, Bs),
	releaseTerminal: Z(y.terminal_release, Vs, X),
	waitForTerminalExit: Z(y.terminal_wait_for_exit, Hs),
	killTerminal: Z(y.terminal_kill, Us, X),
	createElicitation: Z(y.elicitation_create, cc)
}, Sf = {
	sessionUpdate: Q(y.session_update, au),
	completeElicitation: Q(y.elicitation_complete, ou)
}, Cf = vf(yf);
vf(bf);
var wf = vf(xf), Tf = vf(Sf);
function Ef(e, t, n, r) {
	return {
		params: e,
		requestId: r,
		signal: n,
		agent: t
	};
}
function Df(e, t, n) {
	return {
		params: e,
		signal: n,
		agent: t
	};
}
var Of = class {
	activeSessions = /* @__PURE__ */ new Map();
	handleMessage(e) {
		if (e.kind !== "notification" || e.method !== y.session_update) return J.no(e);
		let t = au.parse(e.params), n = {
			kind: "session_update",
			notification: t,
			update: t.update
		}, r = this.activeSessions.get(t.sessionId);
		if (r && r.size > 0) for (let e of r) e.enqueue(n);
		return J.no(e);
	}
	attach(e, t) {
		let n = this.activeSessions.get(e.sessionId) ?? /* @__PURE__ */ new Set();
		return n.add(t), this.activeSessions.set(e.sessionId, n), new qd(() => {
			n.delete(t), n.size === 0 && this.activeSessions.delete(e.sessionId);
		});
	}
}, kf = /* @__PURE__ */ new WeakMap();
function Af(e) {
	let t = kf.get(e);
	return t || (t = new Of(), kf.set(e, t)), t;
}
function jf(e, t) {
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
var Mf = Symbol("appBuilder"), Nf = Symbol("runAgentConnectHandlers"), Pf = Symbol("runClientConnectHandlers"), Ff = { allowBatches: !1 };
function If(e) {
	return new Lf(e);
}
var Lf = class {
	builder = Yd.builder();
	connectHandlers = [];
	constructor(e = {}) {
		e.name && this.builder.name(e.name), this.builder.withHandler({
			handleMessage: (e, t) => Af(t).handleMessage(e),
			describe: () => "client-session-update-router"
		});
	}
	[Mf]() {
		return this.builder;
	}
	[Pf](e) {
		jf(e, this.connectHandlers);
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
		let r = wf[e];
		if (!r) throw Error(`Unknown ACP request method '${e}'. Pass a params parser for custom methods.`);
		return this.request(r, t);
	}
	onNotification(e, t, n) {
		if (n) return this.notification({
			method: e,
			params: t
		}, n);
		let r = Tf[e];
		if (!r) throw Error(`Unknown ACP notification method '${e}'. Pass a params parser for custom methods.`);
		return this.notification(r, t);
	}
	request(e, t) {
		return gf(this.builder, e, (e, t, n, r) => Ef(e, af.create(t, r), n, r), t), this;
	}
	notification(e, t) {
		return _f(this.builder, e, (e, t, n) => Df(e, af.create(t), n), t), this;
	}
	connectConnection(e) {
		if (Qd(e)) {
			let t = this.openStreamConnection(e);
			return this[Pf](t.connection), t;
		}
		let [t, n] = $d(), r = e[Mf]().connect(n, Ff), i = lf(r), a = this.openStreamConnection(t);
		a.rawConnection.closed.then(() => i.close()), r.closed.then(() => a.connection.close());
		try {
			e[Nf](i), this[Pf](a.connection);
		} catch (e) {
			throw i.close(e), a.connection.close(e), e;
		}
		return a;
	}
	openStreamConnection(e) {
		let t = this.builder.connect(e, Ff);
		return {
			rawConnection: t,
			connection: uf(t, this.connectHandlers)
		};
	}
};
v.initialize, v.authenticate, v.providers_list, v.providers_set, v.providers_disable, v.session_new, v.session_load, v.session_set_mode, v.session_set_config_option, v.session_prompt, v.session_list, v.session_delete, v.session_fork, v.session_resume, v.session_close, v.logout, v.nes_start, v.nes_suggest, v.nes_close, v.session_cancel, v.nes_accept, v.nes_reject, v.document_did_open, v.document_did_change, v.document_did_close, v.document_did_save, v.document_did_focus, y.session_request_permission, y.fs_write_text_file, y.fs_read_text_file, y.terminal_create, y.terminal_output, y.terminal_release, y.terminal_wait_for_exit, y.terminal_kill, y.elicitation_create, y.session_update, y.elicitation_complete;
//#endregion
//#region src/core/protocol/types.ts
function Rf(e, t, n, r) {
	if (!Wf(e.cwd)) throw $(`ACP cwd must be an absolute path: ${e.cwd}`, n, r);
	if (e.additionalDirectories?.some((e) => !Wf(e))) throw $("ACP additionalDirectories must contain only absolute paths", n, r);
	if (e.additionalDirectories?.length && !t.additionalDirectories) throw $("The agent does not support additionalDirectories", n, r);
	if ((e.additionalDirectories?.length ?? 0) > 64) throw $("ACP additionalDirectories is limited to 64 entries", n, r);
	if ((e.mcpServers?.length ?? 0) > 32) throw $("ACP MCP configuration is limited to 32 servers", n, r);
	for (let i of e.mcpServers ?? []) Uf(i, t, n, r);
}
function zf(e, t, n) {
	if (e.length > 256) throw $("ACP prompts are limited to 256 content blocks", n, "prompt");
	for (let r of e) if (Hf(r, n), r.type !== "text" && r.type !== "resource_link" && !(r.type === "image" && t.image) && !(r.type === "audio" && t.audio) && !(r.type === "resource" && t.embeddedContext)) throw $(`The agent does not support prompt content type '${r.type}'`, n, "prompt");
}
function Bf(t, n, r) {
	let i = t instanceof Y && [
		-32600,
		-32601,
		-32602
	].includes(t.code), a = t instanceof e && t.accepted !== void 0 ? t.accepted : r && !i;
	return new e(t instanceof e ? t.code : "TURN_INTERRUPTED", t instanceof Error ? t.message : String(t), {
		cause: t,
		protocol: n,
		phase: "prompt",
		retryable: !a,
		accepted: a,
		completionUnknown: t instanceof e && t.completionUnknown !== void 0 ? t.completionUnknown : a && !(t instanceof Y)
	});
}
async function Vf(t, n, r) {
	try {
		return await t();
	} catch (t) {
		throw t instanceof Y ? t.code === -32e3 ? new e("AUTHENTICATION_REQUIRED", "The agent requires authentication for this session operation", {
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
function Hf(e, t) {
	if (e.type === "text" && typeof e.text == "string" && e.text.length > 1048576) throw $("ACP text content is limited to 1 MiB", t, "prompt");
	if ((e.type === "image" || e.type === "audio") && typeof e.data == "string" && e.data.length > 8388608) throw $("ACP media content is limited to 8 MiB of base64 data", t, "prompt");
	if (e.type === "resource" && typeof e.resource == "object" && e.resource !== null) {
		let n = e.resource;
		if (typeof n.text == "string" && n.text.length > 1048576) throw $("ACP embedded resource text is limited to 1 MiB", t, "prompt");
		if (typeof n.blob == "string" && n.blob.length > 8388608) throw $("ACP embedded resource data is limited to 8 MiB", t, "prompt");
	}
}
function Uf(e, t, n, r) {
	if (e.type === "sse" && n !== 1) throw $("SSE MCP servers are available only with protocol: 1", n, r);
	if (!t.mcp[e.type]) throw $(`The agent does not support ${e.type} MCP servers`, n, r);
}
function $(t, n, r) {
	return new e("INVALID_CONFIGURATION", t, {
		...n === void 0 ? {} : { protocol: n },
		phase: r
	});
}
function Wf(e) {
	return e.startsWith("/") || /^[A-Za-z]:[\\/]/.test(e) || e.startsWith("\\\\");
}
//#endregion
//#region src/core/protocol/interactions.ts
function Gf(e) {
	return _(e).map((e, t) => ({
		id: g(e.optionId) ?? `option-${t}`,
		name: g(e.name) ?? `Option ${t + 1}`,
		kind: g(e.kind) ?? "unknown"
	}));
}
function Kf(e) {
	let t = h(e) ? e : {}, n = t.mode === "form" || t.mode === "url" ? t.mode : "unknown", r = g(t.elicitationId), i = ve(t.requestedSchema), a = ge(t.url);
	return {
		type: "elicitation",
		...r ? { elicitationId: r } : {},
		mode: n,
		message: g(t.message) ?? "The agent needs more information.",
		...a ? { url: a } : {},
		...i ? { requestedSchema: i } : {}
	};
}
function qf(e) {
	return { outcome: e };
}
function Jf(e) {
	return e.action === "accept" ? {
		action: "accept",
		...e.content ? { content: Object.fromEntries(Object.entries(e.content).map(([e, t]) => [e, Array.isArray(t) ? [...t] : t])) } : {}
	} : { action: e.action };
}
//#endregion
export { H as A, g as B, R as C, U as D, V as E, La as F, Se as G, h as H, v as I, f as J, Ce as K, le as L, B as M, L as N, P as O, uo as P, ue as R, K as S, F as T, ye as U, ve as V, xe as W, t as X, e as Y, Zd as _, Bf as a, ps as b, Rf as c, Yd as d, J as f, Od as g, Ad as h, qf as i, M as j, z as k, If as l, Y as m, Kf as n, Vf as o, qd as p, d as q, Gf as r, zf as s, Jf as t, ef as u, W as v, I as w, G as x, fs as y, Te as z };

//# sourceMappingURL=interactions.js.map