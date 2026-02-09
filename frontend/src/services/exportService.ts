import { saveAs } from 'file-saver';

export interface PaperFormatExport {
  fontFamilyCss: string;
  fontSize: number;
  lineSpacing: number;
  margins: string;
  firstLineIndent: string;
}

export interface ExportOptions {
  title?: string;
  author?: string;
  includeMetadata?: boolean;
  paperFormat?: PaperFormatExport;
  authorLastName?: string;
  shortenedTitle?: string;
}

export interface ExportResult {
  success: boolean;
  error?: string;
}

/**
 * Generate a sanitized filename with timestamp
 */
export function generateFilename(title: string, extension: string): string {
  const sanitized = title.replace(/[^a-z0-9]/gi, '-').toLowerCase();
  const timestamp = new Date().toISOString().split('T')[0]; // YYYY-MM-DD format
  return `${sanitized}-${timestamp}.${extension}`;
}

/**
 * Extract title from HTML content
 * Priority: H1 tag > first paragraph > "Untitled Document"
 */
export function extractTitle(html: string): string {
  // Try H1 first
  const h1Match = html.match(/<h1[^>]*>(.*?)<\/h1>/i);
  if (h1Match) {
    const title = h1Match[1].replace(/<[^>]*>/g, '').trim();
    if (title) return title;
  }

  // Try first paragraph
  const pMatch = html.match(/<p[^>]*>(.*?)<\/p>/i);
  if (pMatch) {
    const text = pMatch[1].replace(/<[^>]*>/g, '').trim();
    if (text) {
      return text.substring(0, 50) + (text.length > 50 ? '...' : '');
    }
  }

  return 'Untitled Document';
}

/**
 * Add metadata header to HTML content
 */
export function addDocumentMetadata(html: string, options: ExportOptions): string {
  if (!options.includeMetadata) return html;

  const metadata = `
    <div style="margin-bottom: 2em; padding-bottom: 1em; border-bottom: 1px solid #ccc;">
      <p style="margin: 0; font-size: 14px;"><strong>Title:</strong> ${options.title || 'Untitled'}</p>
      <p style="margin: 0; font-size: 14px;"><strong>Date:</strong> ${new Date().toLocaleDateString()}</p>
      ${options.author ? `<p style="margin: 0; font-size: 14px;"><strong>Author:</strong> ${options.author}</p>` : ''}
    </div>
  `;
  return metadata + html;
}

/**
 * Create complete HTML document with embedded styles
 */
function createFullHTMLDocument(html: string, title: string, options: ExportOptions = {}): string {
  const fmt = options.paperFormat;
  const fontFamily = fmt
    ? fmt.fontFamilyCss
    : "'OpenDyslexic', 'Atkinson Hyperlegible', 'Lexie Readable', -apple-system, BlinkMacSystemFont, sans-serif";
  const fontSize = fmt ? `${fmt.fontSize}pt` : '16px';
  const lineHeight = fmt ? fmt.lineSpacing : 1.6;
  const padding = fmt ? fmt.margins : '2rem';
  const textIndent = fmt ? fmt.firstLineIndent : '0';

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title}</title>
  <style>
    body {
      font-family: ${fontFamily};
      font-size: ${fontSize};
      line-height: ${lineHeight};
      color: #2D2A24;
      background-color: ${fmt ? '#fff' : '#FAF6EE'};
      max-width: ${fmt ? 'none' : '800px'};
      margin: 0 auto;
      padding: ${padding};
    }
    h1, h2, h3, h4, h5, h6 {
      margin-top: 1.5em;
      margin-bottom: 0.5em;
      font-weight: 600;
    }
    h1 { font-size: 2em; }
    h2 { font-size: 1.5em; }
    h3 { font-size: 1.25em; }
    p {
      margin-bottom: 1em;
      text-indent: ${textIndent};
    }
    ul, ol {
      margin-bottom: 1em;
      padding-left: 2em;
    }
    li {
      margin-bottom: 0.5em;
    }
    strong {
      font-weight: 600;
    }
    em {
      font-style: italic;
    }
    code {
      font-family: 'Courier New', monospace;
      background-color: #f4f4f4;
      padding: 0.2em 0.4em;
      border-radius: 3px;
    }
    pre {
      background-color: #f4f4f4;
      padding: 1em;
      border-radius: 5px;
      overflow-x: auto;
    }
    blockquote {
      border-left: 3px solid #E07B4C;
      padding-left: 1em;
      margin-left: 0;
      color: #666;
    }
  </style>
</head>
<body>
  ${html}
</body>
</html>`;
}

/**
 * Export document as DOCX
 */
export async function exportDOCX(
  html: string,
  options: ExportOptions = {}
): Promise<ExportResult> {
  try {
    const title = options.title || extractTitle(html);
    const contentWithMetadata = addDocumentMetadata(html, { ...options, title });

    // Dynamically import to avoid crashing the app at load time
    // (html-to-docx uses Node.js modules that fail as top-level imports)
    // @ts-ignore - no types available
    const { default: HTMLtoDOCX } = await import('html-to-docx');
    const fmt = options.paperFormat;
    const docxOptions: any = {
      table: { row: { cantSplit: true } },
      footer: true,
      pageNumber: true,
    };
    if (fmt) {
      docxOptions.font = fmt.fontFamilyCss.split(',')[0].replace(/'/g, '').trim();
      docxOptions.fontSize = fmt.fontSize * 2; // half-points
      docxOptions.margins = { top: 1440, right: 1440, bottom: 1440, left: 1440 }; // 1" = 1440 twips
    }
    const docxBlob = await HTMLtoDOCX(contentWithMetadata, null, docxOptions);

    // Download the file
    const filename = generateFilename(title, 'docx');
    saveAs(docxBlob, filename);

    return { success: true };
  } catch (error) {
    console.error('DOCX export error:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to export DOCX',
    };
  }
}

/**
 * Export document as PDF
 */
export async function exportPDF(
  html: string,
  options: ExportOptions = {}
): Promise<ExportResult> {
  try {
    const title = options.title || extractTitle(html);
    const contentWithMetadata = addDocumentMetadata(html, { ...options, title });

    const fmt = options.paperFormat;

    // Create a temporary container for PDF generation
    const container = document.createElement('div');
    container.innerHTML = contentWithMetadata;
    container.style.fontFamily = fmt
      ? fmt.fontFamilyCss
      : "'OpenDyslexic', 'Atkinson Hyperlegible', 'Lexie Readable', sans-serif";
    container.style.fontSize = fmt ? `${fmt.fontSize}pt` : '14px';
    container.style.lineHeight = fmt ? String(fmt.lineSpacing) : '1.6';
    container.style.color = '#2D2A24';
    container.style.padding = '20px';

    if (fmt) {
      // Apply first-line indent to paragraphs
      container.querySelectorAll('p').forEach((p) => {
        (p as HTMLElement).style.textIndent = fmt.firstLineIndent;
      });
    }

    // PDF configuration — academic formats use letter size with 1" margins
    const pdfMargin = fmt ? 25.4 : 15; // 1 inch = 25.4mm
    const pdfOptions: any = {
      margin: [pdfMargin, pdfMargin, pdfMargin, pdfMargin],
      filename: generateFilename(title, 'pdf'),
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true },
      jsPDF: { unit: 'mm', format: fmt ? 'letter' : 'a4', orientation: 'portrait' },
    };

    // Dynamically import to avoid browser compatibility issues at load time
    // @ts-ignore - types are incomplete
    const { default: html2pdf } = await import('html2pdf.js');
    await html2pdf().set(pdfOptions).from(container).save();

    return { success: true };
  } catch (error) {
    console.error('PDF export error:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to export PDF',
    };
  }
}

/**
 * Export document as HTML
 */
export async function exportHTML(
  html: string,
  options: ExportOptions = {}
): Promise<ExportResult> {
  try {
    const title = options.title || extractTitle(html);
    const contentWithMetadata = addDocumentMetadata(html, { ...options, title });
    const fullHTML = createFullHTMLDocument(contentWithMetadata, title, options);

    // Create blob and download
    const blob = new Blob([fullHTML], { type: 'text/html;charset=utf-8' });
    const filename = generateFilename(title, 'html');
    saveAs(blob, filename);

    return { success: true };
  } catch (error) {
    console.error('HTML export error:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to export HTML',
    };
  }
}

/**
 * Export document as plain text
 */
export async function exportPlainText(
  text: string,
  options: ExportOptions = {}
): Promise<ExportResult> {
  try {
    const title = options.title || 'Untitled Document';
    let content = text;

    // Add metadata if requested
    if (options.includeMetadata) {
      const metadata = [
        `Title: ${title}`,
        `Date: ${new Date().toLocaleDateString()}`,
        options.author ? `Author: ${options.author}` : null,
        '',
        '─'.repeat(50),
        '',
      ]
        .filter(Boolean)
        .join('\n');
      content = metadata + content;
    }

    // Create blob and download
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const filename = generateFilename(title, 'txt');
    saveAs(blob, filename);

    return { success: true };
  } catch (error) {
    console.error('Plain text export error:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to export plain text',
    };
  }
}
