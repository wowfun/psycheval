import { listValue, lower, state } from "./runtime.js";
import { exportCurrentScope, selectServeDetail } from "./serve-catalog.js";
function bindServeExportControls(target) {
  target.querySelectorAll("[data-export-kind]").forEach(button => {
    button.addEventListener("click", event => {
      event.stopPropagation();
      exportCurrentScope(button.dataset.exportKind || "xlsx");
      button.closest("details")?.removeAttribute("open");
    });
  });
}
function bindTrialSelection(root) {
  root.querySelectorAll("tr[data-source-key]").forEach(node => {
    node.setAttribute("tabindex", "0");
    const open = event => {
      if (event.target !== node && event.target?.closest?.("input,button,a,select,textarea,label,[contenteditable='true'],[data-workspace-report-control]")) return;
      event.stopPropagation();
      selectServeDetail(node.dataset.sourceKey, {
        openSidebar: true,
        opener: node,
        openerSelector: `tr[data-source-key="${cssAttributeValue(node.dataset.sourceKey)}"]`,
      });
    };
    node.addEventListener("click", open);
    node.addEventListener("keydown", event => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      open(event);
    });
  });
}
function cssAttributeValue(value) {
  return String(value ?? "").replaceAll("\\", "\\\\").replaceAll('"', '\\"');
}
function firstUserStepSelection(trialKey, view = state.view) {
  const index = listValue(view?.trajectory_meta).findIndex(meta => meta?.trial_key === trialKey);
  const step = listValue(view?.trajectory?.[index >= 0 ? index : 0]?.steps).find(item => {
    return lower(item?.source) === "user" && item?.step_id !== null && item?.step_id !== undefined;
  });
  return step ? { trialKey, stepId: String(step.step_id) } : null;
}
function xlsxTableRows(rows, columns) {
  return [
    columns.map(column => column.label),
    ...rows.map(row => columns.map(column => exportTableText(row, column)))
  ];
}
function exportTableText(row, column) {
  const raw = column.value(row);
  return column.format ? column.format(raw, row) : (raw ?? "-");
}
function xlsxBytesForRows(rows, columns) {
  return zipFiles([
    {
      name: "[Content_Types].xml",
      text: xmlDeclaration() + `<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>`
    },
    {
      name: "_rels/.rels",
      text: xmlDeclaration() + `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`
    },
    {
      name: "xl/workbook.xml",
      text: xmlDeclaration() + `<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Leaderboard" sheetId="1" r:id="rId1"/></sheets></workbook>`
    },
    {
      name: "xl/_rels/workbook.xml.rels",
      text: xmlDeclaration() + `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>`
    },
    {
      name: "xl/worksheets/sheet1.xml",
      text: worksheetXml(xlsxTableRows(rows, columns))
    }
  ]);
}
function xmlDeclaration() {
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>`;
}
function worksheetXml(rows) {
  const sheetData = rows.map((row, rowIndex) => {
    const rowNumber = rowIndex + 1;
    const cells = row.map((value, columnIndex) => {
      const cellRef = `${xlsxColumnName(columnIndex)}${rowNumber}`;
      return `<c r="${cellRef}" t="inlineStr"><is><t>${xmlEsc(value)}</t></is></c>`;
    }).join("");
    return `<row r="${rowNumber}">${cells}</row>`;
  }).join("");
  return xmlDeclaration() + `<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>${sheetData}</sheetData></worksheet>`;
}
function xlsxColumnName(index) {
  let value = index + 1;
  let name = "";
  while (value > 0) {
    const remainder = (value - 1) % 26;
    name = String.fromCharCode(65 + remainder) + name;
    value = Math.floor((value - 1) / 26);
  }
  return name;
}
function xmlEsc(value) {
  return String(value ?? "").replace(/[&<>'"]/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&apos;", '"': "&quot;" }[ch]));
}
function zipFiles(files) {
  const encoder = new TextEncoder();
  const localParts = [];
  const centralParts = [];
  const zipTime = 0;
  const zipDate = 0x0021;
  let offset = 0;
  files.forEach(file => {
    const nameBytes = encoder.encode(file.name);
    const data = encoder.encode(file.text);
    const crc = crc32(data);
    const localHeader = concatBytes([
      u32(0x04034b50), u16(20), u16(0x0800), u16(0), u16(zipTime), u16(zipDate),
      u32(crc), u32(data.length), u32(data.length), u16(nameBytes.length), u16(0),
      nameBytes
    ]);
    localParts.push(localHeader, data);
    centralParts.push(concatBytes([
      u32(0x02014b50), u16(20), u16(20), u16(0x0800), u16(0), u16(zipTime), u16(zipDate),
      u32(crc), u32(data.length), u32(data.length), u16(nameBytes.length),
      u16(0), u16(0), u16(0), u16(0), u32(0), u32(offset), nameBytes
    ]));
    offset += localHeader.length + data.length;
  });
  const centralDirectory = concatBytes(centralParts);
  const end = concatBytes([
    u32(0x06054b50), u16(0), u16(0), u16(files.length), u16(files.length),
    u32(centralDirectory.length), u32(offset), u16(0)
  ]);
  return concatBytes([...localParts, centralDirectory, end]);
}
function u16(value) {
  const bytes = new Uint8Array(2);
  new DataView(bytes.buffer).setUint16(0, value, true);
  return bytes;
}
function u32(value) {
  const bytes = new Uint8Array(4);
  new DataView(bytes.buffer).setUint32(0, value >>> 0, true);
  return bytes;
}
function concatBytes(parts) {
  const length = parts.reduce((total, part) => total + part.length, 0);
  const out = new Uint8Array(length);
  let offset = 0;
  parts.forEach(part => {
    out.set(part, offset);
    offset += part.length;
  });
  return out;
}
let CRC32_TABLE = null;
function crc32(bytes) {
  const table = crc32Table();
  let crc = 0xffffffff;
  bytes.forEach(byte => {
    crc = (crc >>> 8) ^ table[(crc ^ byte) & 0xff];
  });
  return (crc ^ 0xffffffff) >>> 0;
}
function crc32Table() {
  if (CRC32_TABLE) return CRC32_TABLE;
  CRC32_TABLE = Array.from({ length: 256 }, (_, index) => {
    let crc = index;
    for (let bit = 0; bit < 8; bit += 1) {
      crc = (crc & 1) ? (0xedb88320 ^ (crc >>> 1)) : (crc >>> 1);
    }
    return crc >>> 0;
  });
  return CRC32_TABLE;
}
function downloadBlob(filename, mime, blob) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
export {
  CRC32_TABLE,
  bindServeExportControls,
  bindTrialSelection,
  concatBytes,
  crc32,
  crc32Table,
  downloadBlob,
  firstUserStepSelection,
  u16,
  u32,
  worksheetXml,
  xlsxBytesForRows,
  xlsxColumnName,
  xlsxTableRows,
  xmlDeclaration,
  xmlEsc,
  zipFiles,
};
