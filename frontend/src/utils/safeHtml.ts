import DOMPurify from 'dompurify'
import { marked } from 'marked'

const SAFE_TAGS = [
  'a', 'blockquote', 'br', 'code', 'del', 'em', 'h1', 'h2', 'h3', 'h4',
  'h5', 'h6', 'hr', 'img', 'li', 'ol', 'p', 'pre', 'span', 'strong',
  'table', 'tbody', 'td', 'th', 'thead', 'tr', 'u', 'ul'
]

const SAFE_ATTRIBUTES = ['alt', 'class', 'href', 'loading', 'rel', 'src', 'target', 'title']

export function sanitizeHtml(html: string): string {
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: SAFE_TAGS,
    ALLOWED_ATTR: SAFE_ATTRIBUTES,
    ALLOW_DATA_ATTR: false,
    FORBID_TAGS: ['form', 'iframe', 'object', 'script', 'style', 'svg', 'math'],
    FORBID_ATTR: ['style']
  })
}

export function renderSafeMarkdown(content: string): string {
  if (!content) return ''
  const rendered = marked.parse(content, { async: false, breaks: true, gfm: true })
  return sanitizeHtml(typeof rendered === 'string' ? rendered : '')
}

export function renderSafeText(content: string): string {
  const element = document.createElement('div')
  element.textContent = content || ''
  return element.innerHTML.replace(/\r?\n/g, '<br>')
}

export function renderSafeBbCode(content: string): string {
  const escaped = renderSafeText(content).replace(/<br>/g, '\n')
  const converted = escaped
    .replace(/\[b\]([\s\S]*?)\[\/b\]/gi, '<strong>$1</strong>')
    .replace(/\[i\]([\s\S]*?)\[\/i\]/gi, '<em>$1</em>')
    .replace(/\[u\]([\s\S]*?)\[\/u\]/gi, '<u>$1</u>')
    .replace(/\[url=(https?:\/\/[^\]\s]+)\]([\s\S]*?)\[\/url\]/gi, '<a href="$1" target="_blank" rel="noopener noreferrer">$2</a>')
    .replace(/\[img\](https?:\/\/[^\[\s]+)\[\/img\]/gi, '<img src="$1" loading="lazy">')
    .replace(/\n/g, '<br>')
  return sanitizeHtml(converted)
}
