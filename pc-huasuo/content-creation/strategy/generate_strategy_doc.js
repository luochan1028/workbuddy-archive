const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat, HeadingLevel, BorderStyle,
  WidthType, ShadingType, PageNumber, PageBreak, TabStopType, TabStopPosition } = require("docx");

const NODE_PATH = "C:\\Users\\asus\\.workbuddy\\binaries\\node\\workspace\\node_modules";

const BLUE = "2E75B6";
const DARK = "1F2937";
const GRAY = "6B7280";
const RED = "C0392B";
const GREEN = "27AE60";
const ORANGE = "E67E22";
const PURPLE = "8E44AD";
const LIGHT_BLUE = "DBEAFE";
const LIGHT_GREEN = "D1FAE5";
const LIGHT_RED = "FEE2E2";
const LIGHT_ORANGE = "FEF3C7";
const LIGHT_PURPLE = "EDE9FE";
const LIGHT_GRAY = "F3F4F6";

const border = { style: BorderStyle.SINGLE, size: 1, color: "D1D5DB" };
const borders = { top: border, bottom: border, left: border, right: border };
const noBorder = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };

function heading1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 400, after: 200 },
    children: [new TextRun({ text, font: "Microsoft YaHei", size: 36, bold: true, color: BLUE })]
  });
}

function heading2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 300, after: 150 },
    children: [new TextRun({ text, font: "Microsoft YaHei", size: 28, bold: true, color: DARK })]
  });
}

function heading3(text) {
  return new Paragraph({
    spacing: { before: 200, after: 100 },
    children: [new TextRun({ text, font: "Microsoft YaHei", size: 24, bold: true, color: "374151" })]
  });
}

function bodyText(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 120, line: 360 },
    children: [new TextRun({ text, font: "Microsoft YaHei", size: 21, color: opts.color || "374151", bold: opts.bold || false })]
  });
}

function bulletItem(text, opts = {}) {
  return new Paragraph({
    numbering: { reference: opts.ref || "bullets", level: 0 },
    spacing: { after: 80, line: 340 },
    children: [new TextRun({ text, font: "Microsoft YaHei", size: 21, color: opts.color || "374151", bold: opts.bold || false })]
  });
}

function numberedItem(text, opts = {}) {
  return new Paragraph({
    numbering: { reference: opts.ref || "numbers", level: 0 },
    spacing: { after: 80, line: 340 },
    children: [new TextRun({ text, font: "Microsoft YaHei", size: 21, color: opts.color || "374151", bold: opts.bold || false })]
  });
}

function metricRow(label, value, fillColor, valueColor) {
  return new TableRow({
    children: [
      new TableCell({
        borders, width: { size: 3000, type: WidthType.DXA },
        shading: { fill: fillColor, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({ children: [new TextRun({ text: label, font: "Microsoft YaHei", size: 20, color: "374151" })] })]
      }),
      new TableCell({
        borders, width: { size: 6360, type: WidthType.DXA },
        shading: { fill: fillColor, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({ children: [new TextRun({ text: value, font: "Microsoft YaHei", size: 20, color: valueColor, bold: true })] })]
      })
    ]
  });
}

function actionRow(num, action, deadline, status) {
  const colors = { "1": LIGHT_BLUE, "2": LIGHT_GREEN, "3": LIGHT_ORANGE, "4": LIGHT_PURPLE };
  return new TableRow({
    children: [
      new TableCell({
        borders, width: { size: 600, type: WidthType.DXA },
        shading: { fill: colors[num] || LIGHT_GRAY, type: ShadingType.CLEAR },
        margins: { top: 60, bottom: 60, left: 80, right: 80 },
        verticalAlign: "center",
        children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: num, font: "Microsoft YaHei", size: 18, bold: true, color: DARK })] })]
      }),
      new TableCell({
        borders, width: { size: 4960, type: WidthType.DXA },
        margins: { top: 60, bottom: 60, left: 120, right: 120 },
        children: [new Paragraph({ children: [new TextRun({ text: action, font: "Microsoft YaHei", size: 20, color: "374151" })] })]
      }),
      new TableCell({
        borders, width: { size: 2200, type: WidthType.DXA },
        margins: { top: 60, bottom: 60, left: 80, right: 80 },
        children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: deadline, font: "Microsoft YaHei", size: 18, color: GRAY })] })]
      }),
      new TableCell({
        borders, width: { size: 1600, type: WidthType.DXA },
        margins: { top: 60, bottom: 60, left: 80, right: 80 },
        children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: status, font: "Microsoft YaHei", size: 18, color: GRAY })] })]
      })
    ]
  });
}

const doc = new Document({
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers2", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers3", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ]
  },
  styles: {
    default: { document: { run: { font: "Microsoft YaHei", size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: "Microsoft YaHei", color: BLUE },
        paragraph: { spacing: { before: 400, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Microsoft YaHei", color: DARK },
        paragraph: { spacing: { before: 300, after: 150 }, outlineLevel: 1 } },
    ]
  },
  sections: [
    // ===== COVER PAGE =====
    {
      properties: {
        page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } }
      },
      children: [
        new Paragraph({ spacing: { before: 3000 } }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 400 },
          children: [new TextRun({ text: "\u9636\u7ea7\u8dc3\u8fc1\u6218\u7565\u89c4\u5212", font: "Microsoft YaHei", size: 56, bold: true, color: BLUE })]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 200 },
          children: [new TextRun({ text: "\u2014\u2014 \u4ece\u9ad8\u6821\u8bb2\u5e08\u5230\u516c\u5171\u5f71\u54cd\u529b\u4eba\u7269\u7684\u8def\u5f84\u8bbe\u8ba1", font: "Microsoft YaHei", size: 28, color: GRAY })]
        }),
        new Paragraph({ spacing: { before: 600 } }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "\u57fa\u4e8e Bourdieu \u8d44\u672c\u8f6c\u6362\u7406\u8bba \u00b7 \u4e09\u9636\u6bb5\u8dc3\u8fc1\u6846\u67b6", font: "Microsoft YaHei", size: 22, color: GRAY })]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 200 },
          children: [new TextRun({ text: "2026\u5e745\u6708 \u00b7 \u6210\u90fd", font: "Microsoft YaHei", size: 22, color: GRAY })]
        }),
        new Paragraph({ children: [new PageBreak()] }),
      ]
    },

    // ===== MAIN CONTENT =====
    {
      properties: {
        page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } }
      },
      headers: {
        default: new Header({ children: [new Paragraph({
          children: [new TextRun({ text: "\u9636\u7ea7\u8dc3\u8fc1\u6218\u7565\u89c4\u5212", font: "Microsoft YaHei", size: 16, color: GRAY }), new TextRun({ text: "\t\u673a\u5bc6\u6587\u4ef6 \u00b7 \u4ec5\u9650\u672c\u4eba\u9605\u8bfb", font: "Microsoft YaHei", size: 16, color: GRAY })],
          tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }]
        })] })
      },
      footers: {
        default: new Footer({ children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "\u2014 ", font: "Microsoft YaHei", size: 16, color: GRAY }), new TextRun({ children: [PageNumber.CURRENT], font: "Microsoft YaHei", size: 16, color: GRAY }), new TextRun({ text: " \u2014", font: "Microsoft YaHei", size: 16, color: GRAY })]
        })] })
      },
      children: [
        // ===== PART 1: PERSONAL PROFILE =====
        heading1("\u4e00\u3001\u4e2a\u4eba\u73b0\u72b6\u5168\u666f"),

        heading2("1.1 \u57fa\u7840\u4fe1\u606f"),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [3000, 6360],
          rows: [
            metricRow("\u51fa\u751f\u5e74\u4efd", "1988\u5e74\uff08\u73b038\u5c81\uff09", LIGHT_GRAY, DARK),
            metricRow("\u5b9a\u5c45\u57ce\u5e02", "\u6210\u90fd", LIGHT_GRAY, DARK),
            metricRow("\u7b2c\u4e00\u5b66\u5386", "\u897f\u5357\u4ea4\u901a\u5927\u5b66 \u672c\u79d1", LIGHT_GRAY, DARK),
            metricRow("\u5728\u8bfb\u5b66\u5386", "MPA\uff08\u516c\u5171\u7ba1\u7406\u7855\u58eb\uff09", LIGHT_BLUE, BLUE),
            metricRow("\u8fdc\u671f\u89c4\u5212", "\u6fb3\u95e8/\u9a6c\u6765\u897f\u4e9a\u5728\u804c\u535a\u58eb\uff08\u6570\u5b57\u6cbb\u7406/\u6559\u80b2\u6cbb\u7406\uff09", LIGHT_BLUE, BLUE),
            metricRow("\u73b0\u804c", "\u6210\u90fd\u4e1c\u8f6f\u5b66\u9662 \u9ad8\u6821\u8bb2\u5e08", LIGHT_GREEN, GREEN),
            metricRow("\u4ece\u4e1a\u5e74\u9650", "14\u5e74\uff08\u534e\u4e3a + \u4e2d\u56fd\u7535\u4fe1 + \u9ad8\u6821\uff09", LIGHT_GRAY, DARK),
            metricRow("\u7ecf\u6d4e\u72b6\u51b5", "\u6709\u623f\u6709\u8f66\u65e0\u8d37 \u00b7 \u73b0\u91d1\u5145\u88d5", LIGHT_GREEN, GREEN),
          ]
        }),

        heading2("1.2 \u56db\u7c7b\u8d44\u672c\u73b0\u72b6\uff08Bourdieu \u6846\u67b6\uff09"),

        bodyText("\u9636\u7ea7\u8dc3\u8fc1\u7684\u672c\u8d28\u4e0d\u662f\u201c\u8d5a\u66f4\u591a\u94b1\u201d\uff0c\u800c\u662f\u56db\u79cd\u8d44\u672c\u7684\u7cfb\u7edf\u6027\u8f6c\u6362\u3002\u5468\u6d9b\u3001\u6768\u6f9c\u4e4b\u6240\u4ee5\u80fd\u8de8\u8d8a\u9636\u5c42\uff0c\u6838\u5fc3\u673a\u5236\u662f\uff1a\u5229\u7528\u5e73\u53f0\u83b7\u5f97\u7684\u8c61\u5f81\u8d44\u672c\uff0c\u53cd\u5411\u64ac\u52a8\u793e\u4f1a\u8d44\u672c\u548c\u7ecf\u6d4e\u8d44\u672c\uff0c\u5f62\u6210\u6b63\u53cd\u9988\u3002"),

        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [1800, 1200, 3180, 3180],
          rows: [
            new TableRow({
              children: [
                new TableCell({ borders, width: { size: 1800, type: WidthType.DXA }, shading: { fill: "1F2937", type: ShadingType.CLEAR }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
                  children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "\u8d44\u672c\u7c7b\u578b", font: "Microsoft YaHei", size: 18, bold: true, color: "FFFFFF" })] })] }),
                new TableCell({ borders, width: { size: 1200, type: WidthType.DXA }, shading: { fill: "1F2937", type: ShadingType.CLEAR }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
                  children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "\u5f53\u524d\u6c34\u5e73", font: "Microsoft YaHei", size: 18, bold: true, color: "FFFFFF" })] })] }),
                new TableCell({ borders, width: { size: 3180, type: WidthType.DXA }, shading: { fill: "1F2937", type: ShadingType.CLEAR }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
                  children: [new Paragraph({ children: [new TextRun({ text: "\u73b0\u72b6\u8bf4\u660e", font: "Microsoft YaHei", size: 18, bold: true, color: "FFFFFF" })] })] }),
                new TableCell({ borders, width: { size: 3180, type: WidthType.DXA }, shading: { fill: "1F2937", type: ShadingType.CLEAR }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
                  children: [new Paragraph({ children: [new TextRun({ text: "\u6218\u7565\u542b\u4e49", font: "Microsoft YaHei", size: 18, bold: true, color: "FFFFFF" })] })] }),
              ]
            }),
            ...[
              ["\u7ecf\u6d4e\u8d44\u672c", "\u2605\u2605\u2605\u2605\u2605", "\u6709\u623f\u6709\u8f66\u65e0\u8d37\uff0c\u73b0\u91d1\u5145\u88d5", "\u53ef\u627f\u53d7\u957f\u671f\u6295\u5165\uff0c\u7528\u94b1\u6362\u65f6\u95f4\u6362\u5730\u4f4d", LIGHT_GREEN, GREEN],
              ["\u6587\u5316\u8d44\u672c", "\u2605\u2605\u2605\u2606\u2606", "MPA\u5728\u8bfb\uff0c\u672c\u79d1\u51fa\u8eab\u5f85\u8865\uff0c\u535a\u58eb\u672a\u542f\u52a8", "\u5b66\u5386\u95e8\u69db\u662f\u6700\u5927\u74f6\u9888\uff0c\u4f46\u8def\u5f84\u5df2\u6e05\u6670", LIGHT_BLUE, BLUE],
              ["\u793e\u4f1a\u8d44\u672c", "\u2605\u2605\u2606\u2606\u2606", "\u9ad8\u6821/\u0049\u0054\u5708\uff0c\u672a\u5207\u5165\u7701\u7ea7\u667a\u5e93/\u884c\u653f\u5708", "\u5708\u5c42\u662f\u8dc3\u8fc1\u7684\u6838\u5fc3\u6760\u6746\uff0c\u5f53\u524d\u6700\u8584\u5f31", LIGHT_ORANGE, ORANGE],
              ["\u8c61\u5f81\u8d44\u672c", "\u2605\u2606\u2606\u2606\u2606", "\u65e0\u516c\u5171\u5f71\u54cd\u529b\uff0c\u65e0\u5a92\u4f53/\u667a\u5e93\u54c1\u724c\u80cc\u4e66", "\u8fd9\u662f\u5468\u6d9b\u6768\u6f9c\u7684\u6838\u5fc3\u5dee\u5f02\uff0c\u4e5f\u6700\u96be", LIGHT_RED, RED],
            ].map(([type, level, desc, strategy, bg, fg]) =>
              new TableRow({
                children: [
                  new TableCell({ borders, width: { size: 1800, type: WidthType.DXA }, shading: { fill: bg, type: ShadingType.CLEAR }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
                    children: [new Paragraph({ children: [new TextRun({ text: type, font: "Microsoft YaHei", size: 20, bold: true, color: fg })] })] }),
                  new TableCell({ borders, width: { size: 1200, type: WidthType.DXA }, shading: { fill: bg, type: ShadingType.CLEAR }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
                    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: level, font: "Microsoft YaHei", size: 20, color: fg })] })] }),
                  new TableCell({ borders, width: { size: 3180, type: WidthType.DXA }, shading: { fill: bg, type: ShadingType.CLEAR }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
                    children: [new Paragraph({ children: [new TextRun({ text: desc, font: "Microsoft YaHei", size: 18, color: "374151" })] })] }),
                  new TableCell({ borders, width: { size: 3180, type: WidthType.DXA }, shading: { fill: bg, type: ShadingType.CLEAR }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
                    children: [new Paragraph({ children: [new TextRun({ text: strategy, font: "Microsoft YaHei", size: 18, color: fg, bold: true })] })] }),
                ]
              })
            )
          ]
        }),

        new Paragraph({ spacing: { before: 200, after: 100 } }),
        bodyText("\u5468\u6d9b\u8def\u5f84\uff1a\u592e\u89c6\u5e73\u53f0\uff08\u6587\u5316\u2192\u8c61\u5f81\uff09\u2192 \u9752\u6625\u6709\u996d\u5c40\uff08\u8c61\u5f81\u2192\u793e\u4f1a\uff09\u2192 \u6587\u5316\u4ea7\u4e1a\uff08\u793e\u4f1a\u2192\u7ecf\u6d4e\uff09", { color: GRAY }),
        bodyText("\u6768\u6f9c\u8def\u5f84\uff1a\u592e\u89c6\uff08\u6587\u5316\u2192\u8c61\u5f81\uff09\u2192 \u9633\u5149\u536b\u89c6\uff08\u8c61\u5f81\u2192\u7ecf\u6d4e+\u793e\u4f1a\uff09\u2192 \u8fbe\u6c83\u65af/\u6148\u5584\uff08\u793e\u4f1a\u2192\u8c61\u5f81\u2191\uff09", { color: GRAY }),
        bodyText("\u4f60\u7684\u8def\u5f84\uff1a\u7ecf\u6d4e\u2192\u6587\u5316\uff08MPA/\u535a\u58eb\uff09\u2192 \u793e\u4f1a\uff08\u667a\u5e93/\u4e13\u5bb6\u5e93\uff09\u2192 \u8c61\u5f81\uff08\u516c\u5171\u8bdd\u8bed\u6743\uff09\u2192 \u6b63\u53cd\u9988", { color: RED, bold: true }),

        // ===== PART 2: ADVANTAGE ANALYSIS =====
        heading1("\u4e8c\u3001\u6838\u5fc3\u4f18\u52bf\u4e0e\u6218\u7565\u6760\u6746"),

        heading2("2.1 \u56db\u5927\u4f18\u52bf\u7684\u6760\u6746\u8f6c\u5316"),

        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [2340, 3510, 3510],
          rows: [
            new TableRow({
              children: [
                new TableCell({ borders, width: { size: 2340, type: WidthType.DXA }, shading: { fill: "1F2937", type: ShadingType.CLEAR }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
                  children: [new Paragraph({ children: [new TextRun({ text: "\u4f18\u52bf", font: "Microsoft YaHei", size: 18, bold: true, color: "FFFFFF" })] })] }),
                new TableCell({ borders, width: { size: 3510, type: WidthType.DXA }, shading: { fill: "1F2937", type: ShadingType.CLEAR }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
                  children: [new Paragraph({ children: [new TextRun({ text: "\u6760\u6746\u8f6c\u5316\u65b9\u5f0f", font: "Microsoft YaHei", size: 18, bold: true, color: "FFFFFF" })] })] }),
                new TableCell({ borders, width: { size: 3510, type: WidthType.DXA }, shading: { fill: "1F2937", type: ShadingType.CLEAR }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
                  children: [new Paragraph({ children: [new TextRun({ text: "\u5177\u4f53\u64cd\u4f5c", font: "Microsoft YaHei", size: 18, bold: true, color: "FFFFFF" })] })] }),
              ]
            }),
            ...[
              ["\u590d\u5408\u578b\u8d5b\u9053\u7a00\u7f3a", "\u6210\u4e3a\u201c\u6570\u5b57\u6cbb\u7406\u201d\u9886\u57df\u552f\u4e00\u61c2\u6280\u672f+\u61c2\u653f\u7b56\u7684\u4eba", "\u7701\u7ea7\u667a\u5e93\u7f3a\u7684\u5c31\u662f\u8fd9\u79cd\u4eba\u2014\u2014\u7eaf\u6587\u79d1\u4e0d\u61c2\u6280\u672f\uff0c\u7eaf\u5de5\u79d1\u4e0d\u61c2\u653f\u7b56"],
              ["\u9ad8\u6821\u6559\u804c\u8eab\u4efd", "\u7528\u6559\u804c\u7533\u62a5\u7701\u7ea7\u8bfe\u9898+\u8fdb\u5165\u4e13\u5bb6\u5e93", "\u4e13\u5bb6\u5e93\u4e0d\u770b985/211\uff0c\u770b\u804c\u79f0+\u8bfe\u9898\u7ecf\u5386\u2014\u2014\u8fd9\u662f\u4f60\u7684\u7a97\u53e3"],
              ["\u534e\u4e3a/\u7535\u4fe1\u5b9e\u6218", "\u7528\u5b9e\u6218\u6848\u4f8b\u505a\u653f\u7b56\u7814\u7a76\uff0c\u78be\u538b\u7eaf\u6587\u732e\u6d3e", "\u522b\u4eba\u5199\u8bba\u6587\u9760\u5f15\u7528\uff0c\u4f60\u5199\u8bba\u6587\u9760\u4eb2\u8eab\u7ecf\u5386\u2014\u2014\u4fe1\u5ea6\u78be\u538b"],
              ["\u7ecf\u6d4e\u5e95\u5ea7\u7a33\u56fa", "\u81ea\u8d39\u505a\u8bfe\u9898\u3001\u81ea\u8d39\u51fa\u4e66\u3001\u81ea\u8d39\u53c2\u8bbf\u6d77\u5916", "\u5f88\u591a\u8bfe\u9898\u9700\u8981\u914d\u5957\u7ecf\u8d39\u2014\u2014\u522b\u4eba\u6101\u94b1\uff0c\u4f60\u76f4\u63a5\u7528\u94b1\u6362\u65f6\u95f4"],
            ].map(([adv, leverage, action]) =>
              new TableRow({
                children: [
                  new TableCell({ borders, width: { size: 2340, type: WidthType.DXA }, shading: { fill: LIGHT_GRAY, type: ShadingType.CLEAR }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
                    children: [new Paragraph({ children: [new TextRun({ text: adv, font: "Microsoft YaHei", size: 20, bold: true, color: DARK })] })] }),
                  new TableCell({ borders, width: { size: 3510, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
                    children: [new Paragraph({ children: [new TextRun({ text: leverage, font: "Microsoft YaHei", size: 20, color: BLUE })] })] }),
                  new TableCell({ borders, width: { size: 3510, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
                    children: [new Paragraph({ children: [new TextRun({ text: action, font: "Microsoft YaHei", size: 18, color: "374151" })] })] }),
                ]
              })
            )
          ]
        }),

        heading2("2.2 \u4e09\u5927\u77ed\u677f\u7684\u8981\u5bb3\u5206\u6790"),

        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [2000, 2680, 2340, 2340],
          rows: [
            new TableRow({
              children: ["\u77ed\u677f", "\u5177\u4f53\u8868\u73b0", "\u5371\u5bb3\u7b49\u7ea7", "\u5bf9\u51b2\u7b56\u7565"].map(h =>
                new TableCell({ borders, width: { size: 2340, type: WidthType.DXA }, shading: { fill: "1F2937", type: ShadingType.CLEAR }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
                  children: [new Paragraph({ children: [new TextRun({ text: h, font: "Microsoft YaHei", size: 18, bold: true, color: "FFFFFF" })] })] }))
            }),
            ...[
              ["\u4efb\u6559\u9662\u6821\u5c42\u7ea7", "\u4e1c\u8f6f\u5b66\u9662\u4e3a\u6c11\u529e\u4e8c\u672c\uff0c\u5b58\u5728\u51fa\u8eab\u504f\u89c1", "\u2605\u2605\u2605\u2606\u2606", "\u6d77\u5916\u535a\u58eb\u8865\u4f4d+\u8bfe\u9898\u6210\u679c\u8986\u76d6\u51fa\u8eab"],
              ["\u5c65\u5386\u7a7a\u767d", "\u65e0\u4f53\u5236\u5185\u653f\u7b56\u8c03\u7814\u3001\u6838\u5fc3\u6587\u7a3f\u8d77\u8349\u7ecf\u5386", "\u2605\u2605\u2605\u2605\u2606", "\u7528MPA\u8bfe\u9898\u4f5c\u4e3a\u9996\u6b21\u7a81\u7834\u53e3"],
              ["\u4eba\u8109\u5708\u5c42", "\u672a\u5bf9\u63a5\u7701\u7ea7\u51b3\u7b56\u54a8\u8be2\u3001\u9ad8\u7aef\u667a\u5e93\u5708\u5b50", "\u2605\u2605\u2605\u2605\u2605", "\u5148\u901a\u8fc7\u8bfe\u9898\u5408\u4f5c\u7834\u5708\uff0c\u518d\u7528\u6210\u679c\u64ac\u52a8\u5708\u5c42"],
            ].map(([shortage, detail, level, strategy]) =>
              new TableRow({
                children: [
                  new TableCell({ borders, width: { size: 2000, type: WidthType.DXA }, shading: { fill: LIGHT_RED, type: ShadingType.CLEAR }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
                    children: [new Paragraph({ children: [new TextRun({ text: shortage, font: "Microsoft YaHei", size: 20, bold: true, color: RED })] })] }),
                  new TableCell({ borders, width: { size: 2680, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
                    children: [new Paragraph({ children: [new TextRun({ text: detail, font: "Microsoft YaHei", size: 18, color: "374151" })] })] }),
                  new TableCell({ borders, width: { size: 2340, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
                    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: level, font: "Microsoft YaHei", size: 18, color: RED })] })] }),
                  new TableCell({ borders, width: { size: 2340, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
                    children: [new Paragraph({ children: [new TextRun({ text: strategy, font: "Microsoft YaHei", size: 18, color: BLUE })] })] }),
                ]
              })
            )
          ]
        }),

        // ===== PART 3: THREE-PHASE PATH =====
        heading1("\u4e09\u3001\u4e09\u9636\u6bb5\u8dc3\u8fc1\u8def\u5f84"),

        heading2("Phase 1\uff1a\u592f\u57fa\uff081-2\u5e74\uff09\u2014\u2014 \u8d44\u672c\u8f6c\u6362\uff1a\u7ecf\u6d4e\u2192\u6587\u5316+\u793e\u4f1a"),
        bodyText("\u6838\u5fc3\u76ee\u6807\uff1a\u62ff\u5230\u7701\u7ea7\u4e13\u5bb6\u5e93\u5165\u573a\u5238\uff0c\u5b8c\u6210\u4ece\u201c\u6559\u5e08\u201d\u5230\u201c\u4e13\u5bb6\u201d\u7684\u8eab\u4efd\u8f6c\u6362\u3002", { bold: true }),

        heading3("\u5b66\u672f\u7ebf"),
        numberedItem("MPA\u8bba\u6587\u9009\u9898\u9501\u5b9a\u201c\u56db\u5ddd\u7701\u6570\u5b57\u653f\u5e9c\u5efa\u8bbe\u73b0\u72b6\u4e0e\u8def\u5f84\u7814\u7a76\u201d\uff0c\u4ee5\u4f18\u79c0\u7b49\u7ea7\u6bd5\u4e1a", { ref: "numbers" }),
        numberedItem("\u5728\u8bfb\u671f\u95f4\u53d1\u88682-3\u7bc7\u6838\u5fc3\u671f\u520a/CSSCI\u653f\u7b56\u8bba\u6587\uff0c\u4e3b\u9898\u56f4\u7ed5\u201c\u6570\u5b57\u6cbb\u7406+\u5730\u65b9\u5b9e\u8df5\u201d", { ref: "numbers" }),
        numberedItem("\u5229\u7528\u534e\u4e3a/\u7535\u4fe1\u7684\u653f\u4f01\u4e91\u9879\u76ee\u7ecf\u5386\uff0c\u5c06\u5b9e\u6218\u6848\u4f8b\u8f6c\u5316\u4e3a\u653f\u7b56\u7814\u7a76\u7d20\u6750", { ref: "numbers" }),

        heading3("\u5708\u5c42\u7ebf"),
        numberedItem("\u901a\u8fc7MPA\u540c\u5b66\u5708\uff08\u4f53\u5236\u5185\u4e2d\u5757\u529b\u91cf\uff09\u5efa\u7acb\u9996\u6279\u7701\u7ea7\u90e8\u95e8\u5173\u7cfb", { ref: "numbers2" }),
        numberedItem("\u4e3b\u52a8\u7533\u62a5\u56db\u5ddd\u7701\u79d1\u6280\u5385/\u5927\u6570\u636e\u5c40\u7684\u6570\u5b57\u653f\u5e9c\u4e13\u5bb6\u5e93", { ref: "numbers2" }),
        numberedItem("\u5728\u5ddd\u5927/\u7535\u79d1\u5927\u505a1\u6b21\u4ee5\u4e0a\u5b66\u672f\u5206\u4eab\uff0c\u5efa\u7acb\u9996\u6279\u5b66\u672f\u5708\u8054\u7cfb", { ref: "numbers2" }),
        numberedItem("\u4ee5\u201c\u6570\u5b57\u6cbb\u7406\u201d\u4e3a\u5173\u952e\u8bcd\uff0c\u4e3b\u52a8\u53c2\u4e0e\u7701\u7ea7\u51b66\u6b21\u4ee5\u4e0a\u653f\u7b56\u8bba\u575b/\u7814\u8ba8\u4f1a", { ref: "numbers2" }),

        heading3("\u5a92\u4f53\u7ebf"),
        numberedItem("\u5f00\u8bbe\u516c\u4f17\u53f7/\u6296\u97f3\u8d26\u53f7\uff0c\u5b9a\u4f4d\u201c\u6570\u5b57\u6cbb\u7406\u89c2\u5bdf\u201d\uff0c\u6bcf\u5468\u53d12\u6761\u653f\u7b56\u89e3\u8bfb\u77ed\u89c6\u9891", { ref: "numbers3" }),
        numberedItem("\u7ed3\u5408AI\u7f16\u7a0b\u5185\u5bb9\u7ecf\u9a8c\uff0c\u505a\u201cAI+\u653f\u5e9c\u201d\u4ea4\u53c9\u89c6\u89d2\u5185\u5bb9\uff0c\u5f62\u6210\u5dee\u5f02\u5316", { ref: "numbers3" }),

        bodyText("\u5173\u952e\u91cc\u7a0b\u7891\uff1a\u62ff\u5230\u7701\u7ea7\u4e13\u5bb6\u5e93\u5165\u573a\u5238 + \u7b2c\u4e00\u4efd\u5185\u53c2/\u653f\u7b56\u5efa\u8bae\u83b7\u6279\u793a", { color: RED, bold: true }),

        heading2("Phase 2\uff1a\u7834\u5708\uff083-5\u5e74\uff09\u2014\u2014 \u8d44\u672c\u8f6c\u6362\uff1a\u6587\u5316+\u793e\u4f1a\u2192\u8c61\u5f81"),
        bodyText("\u6838\u5fc3\u76ee\u6807\uff1a\u4ece\u201c\u4e13\u5bb6\u201d\u8fbe\u6210\u201c\u516c\u5171\u77e5\u8bc6\u5206\u5b50\u201d\uff0c\u83b7\u5f97\u5a92\u4f53\u548c\u667a\u5e93\u7684\u53cc\u91cd\u80cc\u4e66\u3002", { bold: true }),

        heading3("\u5b66\u672f\u7ebf"),
        numberedItem("\u542f\u52a8\u6fb3\u95e8/\u9a6c\u6765\u897f\u4e9a\u5728\u804c\u535a\u58eb\uff0c\u65b9\u5411\u9501\u5b9a\u6570\u5b57\u6cbb\u7406/\u6559\u80b2\u6cbb\u7406", { ref: "numbers" }),
        numberedItem("\u535a\u58eb\u8bba\u6587\u9009\u9898\u7d27\u6263\u201c\u56db\u5ddd\u6570\u5b57\u6cbb\u7406\u5b9e\u8df5\u201d\uff0c\u4e3a\u540e\u7eed\u667a\u5e93\u5165\u804c\u94fa\u8def", { ref: "numbers" }),

        heading3("\u5708\u5c42\u7ebf"),
        numberedItem("\u53c2\u4e0e\u7701\u7ea7\u51b3\u7b56\u54a8\u8be2\u8bfe\u9898\uff0c\u79ef\u7d2f3\u4efd\u4ee5\u4e0a\u5185\u53c2\u6210\u679c", { ref: "numbers2" }),
        numberedItem("\u4ece\u201c\u4e13\u5bb6\u5e93\u6210\u5458\u201d\u5347\u7ea7\u4e3a\u201c\u8bfe\u9898\u8d1f\u8d23\u4eba\u201d\uff0c\u4e3b\u6301\u7701\u7ea7\u6570\u5b57\u6cbb\u7406\u76f8\u5173\u8bfe\u9898", { ref: "numbers2" }),
        numberedItem("\u5efa\u7acb\u4e0e\u56db\u5ddd\u7701\u59d4\u653f\u7b56\u7814\u7a76\u5ba4\u3001\u7701\u79d1\u534f\u667a\u5e93\u7684\u5e38\u6001\u5316\u5408\u4f5c", { ref: "numbers2" }),

        heading3("\u5a92\u4f53\u7ebf"),
        numberedItem("\u6210\u4e3a\u56db\u5ddd\u536b\u89c6/\u6210\u90fd\u7535\u89c6\u53f0\u6570\u5b57\u653f\u7b56\u89e3\u8bfb\u5609\u5bbe\uff0c\u9996\u6b21\u7535\u89c6\u51fa\u955c\u662f\u8c61\u5f81\u8d44\u672c\u7684\u8df3\u8dc3\u70b9", { ref: "numbers3" }),
        numberedItem("\u4e2a\u4ebaIP\u4ece\u201cAI\u7f16\u7a0b\u201d\u5411\u201c\u6570\u5b57\u6cbb\u7406\u8bc4\u8bba\u5458\u201d\u8f6c\u578b\uff0c\u5185\u5bb9\u8d28\u611f\u5347\u7ea7", { ref: "numbers3" }),
        numberedItem("\u53d1\u5e03\u300a\u56db\u5ddd\u6570\u5b57\u6cbb\u7406\u5e74\u5ea6\u89c2\u5bdf\u62a5\u544a\u300b\uff0c\u6811\u7acb\u884c\u4e1a\u6807\u6746", { ref: "numbers3" }),

        bodyText("\u5173\u952e\u91cc\u7a0b\u7891\uff1a\u9996\u6b21\u7535\u89c6/\u8bba\u575b\u51fa\u955c + \u535a\u58eb\u5f55\u53d6 + \u5185\u53c2\u83b7\u6279\u793a", { color: RED, bold: true }),

        heading2("Phase 3\uff1a\u5347\u7ef4\uff085-10\u5e74\uff09\u2014\u2014 \u8d44\u672c\u8f6c\u6362\uff1a\u8c61\u5f81\u2192\u5168\u90e8\u8d44\u672c\u6b63\u53cd\u9988"),
        bodyText("\u6838\u5fc3\u76ee\u6807\uff1a\u6210\u4e3a\u56db\u5ddd\u7701\u6570\u5b57\u6cbb\u7406\u9886\u57df Top5 \u516c\u4f17\u4eba\u7269\uff0c\u5b9e\u73b0\u8c61\u5f81\u8d44\u672c\u5bf9\u5176\u4ed6\u8d44\u672c\u7684\u6b63\u5411\u64ac\u52a8\u3002", { bold: true }),

        numberedItem("\u535a\u58eb\u6bd5\u4e1a\uff0c\u51b2\u51fb\u516c\u529e\u9ad8\u6821/\u7701\u7ea7\u667a\u5e93\u7814\u7a76\u5458\u5c97\u4f4d", { ref: "numbers" }),
        numberedItem("\u4e3b\u7b14\u7701\u7ea7\u6570\u5b57\u6cbb\u7406\u89c4\u5212/\u767d\u76ae\u4e66\uff0c\u6210\u4e3a\u653f\u7b56\u8bdd\u8bed\u5f15\u9886\u8005", { ref: "numbers" }),
        numberedItem("\u4e3b\u6301\u9ad8\u7aef\u8bba\u575b/\u5cf0\u4f1a\uff0c\u6210\u4e3a\u201c\u6570\u5b57\u6cbb\u7406\u201d\u9886\u57df\u7b2c\u4e00\u8054\u60f3\u4eba", { ref: "numbers" }),
        numberedItem("\u521b\u529e\u667a\u5e93/\u7814\u7a76\u9662\u6216\u8fdb\u5165\u7701\u7ea7\u51b3\u7b56\u54a8\u8be2\u59d4\u5458\u4f1a", { ref: "numbers" }),
        numberedItem("\u8de8\u57df\u62d3\u5c55\uff1a\u4ece\u6570\u5b57\u6cbb\u7406\u5ef6\u4f38\u5230\u6559\u80b2\u6cbb\u7406\u3001\u57ce\u5e02\u6cbb\u7406\uff0c\u6210\u4e3a\u201c\u6cbb\u7406\u201d\u7c7b\u516c\u5171\u77e5\u8bc6\u5206\u5b50", { ref: "numbers" }),

        bodyText("\u5173\u952e\u91cc\u7a0b\u7891\uff1a\u6210\u4e3a\u56db\u5ddd\u7701\u6570\u5b57\u6cbb\u7406\u9886\u57df Top5 \u516c\u4f17\u4eba\u7269", { color: RED, bold: true }),

        // ===== PART 4: ACTION TIMELINE =====
        heading1("\u56db\u3001\u5173\u952e\u884c\u52a8\u65f6\u95f4\u8868"),

        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [600, 4960, 2200, 1600],
          rows: [
            new TableRow({
              children: ["#", "\u884c\u52a8\u4e8b\u9879", "\u622a\u6b62\u65f6\u95f4", "\u72b6\u6001"].map(h =>
                new TableCell({ borders, width: { size: 2340, type: WidthType.DXA }, shading: { fill: "1F2937", type: ShadingType.CLEAR }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
                  children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: h, font: "Microsoft YaHei", size: 18, bold: true, color: "FFFFFF" })] })] }))
            }),
            ...[
              ["1", "MPA\u8bba\u6587\u5f00\u9898\uff1a\u56db\u5ddd\u7701\u6570\u5b57\u653f\u5e9c\u5efa\u8bbe\u7814\u7a76", "2026 Q3", "\u5f85\u542f\u52a8"],
              ["2", "\u9996\u7bc7CSSCI\u653f\u7b56\u8bba\u6587\u6295\u7a3f", "2026 Q4", "\u5f85\u542f\u52a8"],
              ["3", "\u7533\u62a5\u56db\u5ddd\u7701\u6570\u5b57\u653f\u5e9c\u4e13\u5bb6\u5e93", "2027 Q1", "\u5f85\u542f\u52a8"],
              ["4", "\u5f00\u8bbe\u201c\u6570\u5b57\u6cbb\u7406\u89c2\u5bdf\u201d\u516c\u4f17\u53f7", "2026 Q3", "\u5f85\u542f\u52a8"],
              ["2", "\u53c2\u4e0e\u9996\u4e2a\u7701\u7ea7\u653f\u7b56\u8bba\u575b", "2027 Q2", "\u5f85\u542f\u52a8"],
              ["3", "\u542f\u52a8\u6fb3\u95e8/\u9a6c\u6765\u535a\u58eb\u7533\u8bf7", "2027 Q4", "\u5f85\u542f\u52a8"],
              ["4", "\u53d1\u5e03\u9996\u4efd\u5185\u53c2/\u653f\u7b56\u5efa\u8bae", "2028 Q2", "\u5f85\u542f\u52a8"],
              ["1", "\u9996\u6b21\u7535\u89c6\u53f0\u653f\u7b56\u89e3\u8bfb\u51fa\u955c", "2028 Q4", "\u5f85\u542f\u52a8"],
              ["2", "\u4e3b\u6301\u9996\u4e2a\u7701\u7ea7\u667a\u5e93\u8bfe\u9898", "2029 Q2", "\u5f85\u542f\u52a8"],
            ].map(([num, action, deadline, status]) => actionRow(num, action, deadline, status))
          ]
        }),

        // ===== PART 5: RISK & HEDGING =====
        heading1("\u4e94\u3001\u98ce\u9669\u8bc6\u522b\u4e0e\u5bf9\u51b2"),

        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [2000, 2680, 2340, 2340],
          rows: [
            new TableRow({
              children: ["\u98ce\u9669", "\u5177\u4f53\u573a\u666f", "\u6982\u7387", "\u5bf9\u51b2\u7b56\u7565"].map(h =>
                new TableCell({ borders, width: { size: 2340, type: WidthType.DXA }, shading: { fill: "1F2937", type: ShadingType.CLEAR }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
                  children: [new Paragraph({ children: [new TextRun({ text: h, font: "Microsoft YaHei", size: 18, bold: true, color: "FFFFFF" })] })] }))
            }),
            ...[
              ["\u535a\u58eb\u7533\u8bf7\u5931\u8d25", "\u6fb3\u95e8/\u9a6c\u6765\u535a\u58eb\u7ade\u4e89\u52a0\u5267\uff0c\u672a\u83b7\u5f55\u53d6", "\u4e2d", "\u540c\u6b65\u7533\u8bf7\u9999\u6e2f/\u6cf0\u56fd\u5907\u9009\uff0c\u4fdd\u6301\u591a\u7ebf\u63a8\u8fdb"],
              ["\u4e13\u5bb6\u5e93\u5165\u5e93\u53d7\u963b", "\u9662\u6821\u5c42\u7ea7\u88ab\u9690\u5f62\u6b67\u89c6\uff0c\u8bfe\u9898\u6210\u679c\u4e0d\u8db3", "\u4e2d", "\u5148\u4ece\u5e02\u7ea7\u4e13\u5bb6\u5e93\u5165\u624b\uff0c\u518d\u5411\u7701\u7ea7\u8df3"],
              ["\u5a92\u4f53\u8f6c\u578b\u5931\u8d25", "\u4e2a\u4ebaIP\u65e0\u6cd5\u4ece\u201cAI\u7f16\u7a0b\u201d\u8f6c\u578b\u4e3a\u201c\u6570\u5b57\u6cbb\u7406\u201d", "\u4f4e", "\u4e24\u4e2a\u8d26\u53f7\u5e76\u884c\u8fd0\u8425\uff0c\u4e0d\u5f3a\u884c\u8f6c\u578b"],
              ["\u653f\u7b56\u73af\u5883\u53d8\u5316", "\u6570\u5b57\u6cbb\u7406\u8bdd\u9898\u964d\u6e29\uff0c\u667a\u5e93\u9700\u6c42\u840e\u7f29", "\u4f4e", "\u4fdd\u6301\u201c\u6570\u5b57+\u6559\u80b2\u201d\u53cc\u8f68\u80fd\u529b\uff0c\u59cb\u7ec8\u6709\u5907\u9009\u8d5b\u9053"],
              ["\u6253\u5de5\u65f6\u95f4\u4e0d\u8db3", "\u6559\u5b66\u4efb\u52a1\u91cd+\u5b66\u4e1a\u4efb\u52a1\u91cd\uff0c\u65e0\u6cd5\u5e76\u884c", "\u4e2d", "\u7528\u7ecf\u6d4e\u8d44\u672c\u8d2d\u4e70\u65f6\u95f4\uff1a\u51cf\u8bfe\u3001\u96c7\u52a9\u624b\u3001\u5916\u5305\u7814\u7a76"],
            ].map(([risk, detail, prob, strategy]) =>
              new TableRow({
                children: [
                  new TableCell({ borders, width: { size: 2000, type: WidthType.DXA }, shading: { fill: LIGHT_ORANGE, type: ShadingType.CLEAR }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
                    children: [new Paragraph({ children: [new TextRun({ text: risk, font: "Microsoft YaHei", size: 20, bold: true, color: ORANGE })] })] }),
                  new TableCell({ borders, width: { size: 2680, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
                    children: [new Paragraph({ children: [new TextRun({ text: detail, font: "Microsoft YaHei", size: 18, color: "374151" })] })] }),
                  new TableCell({ borders, width: { size: 2340, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
                    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: prob, font: "Microsoft YaHei", size: 20, bold: true, color: prob === "\u4e2d" ? ORANGE : GREEN })] })] }),
                  new TableCell({ borders, width: { size: 2340, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
                    children: [new Paragraph({ children: [new TextRun({ text: strategy, font: "Microsoft YaHei", size: 18, color: BLUE })] })] }),
                ]
              })
            )
          ]
        }),

        // ===== PART 6: CRITICAL INSIGHT =====
        heading1("\u516d\u3001\u6838\u5fc3\u6d1e\u5bdf\uff1a\u4f60\u548c\u5468\u6d9b\u6768\u6f9c\u7684\u8def\u5f84\u5dee\u5f02"),

        bodyText("\u5468\u6d9b\u3001\u6768\u6f9c\u7684\u6838\u5fc3\u4e0d\u662f\u201c\u4e3b\u6301\u4eba\u201d\uff0c\u800c\u662f\u201c\u6587\u5316\u8d44\u672c\u8f6c\u6362\u5668\u201d\u3002\u5979\u4eec\u7684\u8def\u5f84\u662f\u4ece\u201c\u5e73\u53f0\u8c61\u5f81\u8d44\u672c\u201d\u53cd\u5411\u64ac\u52a8\u4e0b\u6e38\u8d44\u672c\u3002\u4f60\u6ca1\u6709\u8fd9\u4e2a\u5e73\u53f0\uff0c\u4f46\u4f60\u6709\u5979\u4eec\u6ca1\u6709\u7684\u4e1c\u897f\uff1a\u7ecf\u6d4e\u5e95\u5ea7\u548c\u590d\u5408\u578b\u4e13\u4e1a\u80fd\u529b\u3002", { bold: true }),

        heading3("\u5468\u6d9b\u6768\u6f9c\u7684\u8dc3\u8fc1\u673a\u5236"),
        bulletItem("\u7b2c\u4e00\u6b65\uff1a\u901a\u8fc7\u592e\u89c6\u5e73\u53f0\u83b7\u5f97\u5de8\u91cf\u8c61\u5f81\u8d44\u672c\uff08\u5168\u56fd\u8ba4\u77e5\uff09"),
        bulletItem("\u7b2c\u4e8c\u6b65\uff1a\u7528\u8c61\u5f81\u8d44\u672c\u64ac\u52a8\u793e\u4f1a\u8d44\u672c\uff08\u8fdb\u5165\u9ad8\u7aef\u5708\u5c42\uff09"),
        bulletItem("\u7b2c\u4e09\u6b65\uff1a\u7528\u793e\u4f1a\u8d44\u672c\u64ac\u52a8\u7ecf\u6d4e\u8d44\u672c\uff08\u521b\u4e1a/\u6295\u8d44\uff09"),
        bulletItem("\u7b2c\u56db\u6b65\uff1a\u7ecf\u6d4e\u8d44\u672c\u56de\u6d41\u5f3a\u5316\u8c61\u5f81\u8d44\u672c\uff08\u6b63\u53cd\u9988\u5faa\u73af\uff09"),

        heading3("\u4f60\u7684\u8dc3\u8fc1\u673a\u5236\uff08\u53cd\u5411\uff09"),
        bulletItem("\u7b2c\u4e00\u6b65\uff1a\u7528\u7ecf\u6d4e\u8d44\u672c\u6362\u6587\u5316\u8d44\u672c\uff08MPA/\u535a\u58eb/\u8bfe\u9898\uff09", { bold: true }),
        bulletItem("\u7b2c\u4e8c\u6b65\uff1a\u7528\u6587\u5316\u8d44\u672c\u6362\u793e\u4f1a\u8d44\u672c\uff08\u4e13\u5bb6\u5e93/\u667a\u5e93/\u5708\u5c42\uff09", { bold: true }),
        bulletItem("\u7b2c\u4e09\u6b65\uff1a\u7528\u793e\u4f1a\u8d44\u672c\u6362\u8c61\u5f81\u8d44\u672c\uff08\u5a92\u4f53\u51fa\u955c/\u8bba\u575b\u4e3b\u6301/\u516c\u5171\u53d1\u58f0\uff09", { bold: true }),
        bulletItem("\u7b2c\u56db\u6b65\uff1a\u8c61\u5f81\u8d44\u672c\u56de\u6d41\u5f3a\u5316\u6240\u6709\u8d44\u672c\uff08\u6b63\u53cd\u9988\u5faa\u73af\uff09", { bold: true }),

        bodyText("\u4f60\u7684\u8def\u5f84\u6bd4\u5468\u6d9b\u6768\u6f9c\u591a\u4e00\u6b65\uff0c\u4f46\u8d77\u70b9\u66f4\u7a33\u3002\u5173\u952e\u662f\u7b2c\u4e09\u6b65\u2014\u2014\u4ece\u201c\u4e13\u5bb6\u201d\u5230\u201c\u516c\u5171\u4eba\u7269\u201d\u7684\u8df3\u8dc3\uff0c\u8fd9\u662f\u6574\u4e2a\u89c4\u5212\u4e2d\u6700\u96be\u7684\u4e00\u6b65\u3002\u5fc5\u987b\u6709\u4e00\u4e2a\u201c\u51fa\u5708\u4e8b\u4ef6\u201d\u6765\u5b8c\u6210\u8fd9\u4e2a\u8df3\u8dc3\u3002", { color: RED }),

        heading3("\u4ec0\u4e48\u662f\u201c\u51fa\u5708\u4e8b\u4ef6\u201d\uff1f"),
        bulletItem("\u4e3b\u7b14\u4e00\u4efd\u88ab\u7701\u9886\u5bfc\u6279\u793a\u7684\u5185\u53c2"),
        bulletItem("\u5728\u91cd\u5927\u653f\u7b56\u8bba\u575b\u4e0a\u505a\u4e3b\u65e8\u6f14\u8bb2\uff0c\u88ab\u5a92\u4f53\u5e7f\u6cdb\u62a5\u9053"),
        bulletItem("\u4e3b\u6301\u4e00\u4e2a\u88ab\u5168\u7701\u5173\u6ce8\u7684\u6570\u5b57\u6cbb\u7406\u767d\u76ae\u4e66\u53d1\u5e03"),
        bulletItem("\u5728\u91cd\u5927\u516c\u5171\u4e8b\u4ef6\u4e2d\u4ee5\u4e13\u5bb6\u8eab\u4efd\u53d1\u58f0\uff0c\u83b7\u5f97\u5168\u7701\u5173\u6ce8"),

        // ===== PART 7: STRATEGIC ANCHOR =====
        heading1("\u4e03\u3001\u6218\u7565\u951a\u70b9"),

        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [9360],
          rows: [
            new TableRow({
              children: [
                new TableCell({
                  borders: { top: { style: BorderStyle.SINGLE, size: 3, color: RED }, bottom: { style: BorderStyle.SINGLE, size: 3, color: RED }, left: { style: BorderStyle.SINGLE, size: 3, color: RED }, right: { style: BorderStyle.SINGLE, size: 3, color: RED } },
                  width: { size: 9360, type: WidthType.DXA },
                  shading: { fill: LIGHT_RED, type: ShadingType.CLEAR },
                  margins: { top: 200, bottom: 200, left: 200, right: 200 },
                  children: [
                    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, children: [new TextRun({ text: "\u6218\u7565\u951a\u70b9", font: "Microsoft YaHei", size: 28, bold: true, color: RED })] }),
                    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, children: [new TextRun({ text: "\u6570\u5b57\u6cbb\u7406 \u00d7 \u56db\u5ddd \u00d7 \u8de8\u754c = \u4f60\u72ec\u6709\u7684\u7ade\u4e89\u58c1\u5792", font: "Microsoft YaHei", size: 24, bold: true, color: DARK })] }),
                    new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "\u4e0d\u505a\u7b2c\u4e8c\u4e2a\u4eba\uff0c\u505a\u7b2c\u4e00\u4e2a\u8fd9\u6837\u7684\u4eba", font: "Microsoft YaHei", size: 22, color: GRAY })] }),
                  ]
                })
              ]
            })
          ]
        }),

        new Paragraph({ spacing: { before: 300 } }),

        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [9360],
          rows: [
            new TableRow({
              children: [
                new TableCell({
                  borders: { top: { style: BorderStyle.SINGLE, size: 3, color: BLUE }, bottom: { style: BorderStyle.SINGLE, size: 3, color: BLUE }, left: { style: BorderStyle.SINGLE, size: 3, color: BLUE }, right: { style: BorderStyle.SINGLE, size: 3, color: BLUE } },
                  width: { size: 9360, type: WidthType.DXA },
                  shading: { fill: LIGHT_BLUE, type: ShadingType.CLEAR },
                  margins: { top: 200, bottom: 200, left: 200, right: 200 },
                  children: [
                    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, children: [new TextRun({ text: "\u6838\u5fc3\u539f\u5219", font: "Microsoft YaHei", size: 28, bold: true, color: BLUE })] }),
                    new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "\u6bcf\u4e00\u6b65\u90fd\u8981\u8ba9\u4e0b\u4e00\u6b65\u66f4\u5bb9\u6613\uff0c\u800c\u4e0d\u662f\u91cd\u65b0\u5f00\u59cb", font: "Microsoft YaHei", size: 22, color: DARK })] }),
                  ]
                })
              ]
            })
          ]
        }),
      ]
    }
  ]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("C:\\Users\\asus\\WorkBuddy\\2026-05-30-19-22-39\\阶级跃迁战略规划.docx", buffer);
  console.log("Document created successfully!");
});
