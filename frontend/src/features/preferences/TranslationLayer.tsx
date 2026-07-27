import { useEffect, useRef } from 'react';

import { translate } from '@/features/preferences/translations';
import { useTranslation } from '@/features/preferences/useTranslation';

interface TextRecord { source: string; rendered: string; }
type AttributeRecord = Record<string, TextRecord>;

const ignoredTags = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEXTAREA']);
const translatableAttributes = ['placeholder', 'title', 'aria-label'];

/**
 * Applies the central translation catalogue to component text and Material UI attributes.
 * This keeps legacy screens localized while new screens can use `useTranslation().t` directly.
 */
export function TranslationLayer() {
  const { language } = useTranslation();
  const textRecords = useRef(new WeakMap<Text, TextRecord>());
  const attributeRecords = useRef(new WeakMap<Element, AttributeRecord>());

  useEffect(() => {
    document.documentElement.lang = language;
    const translateTextNode = (node: Text) => {
      if (!node.parentElement || ignoredTags.has(node.parentElement.tagName)) return;
      const current = node.nodeValue ?? '';
      if (!current.trim()) return;
      const previous = textRecords.current.get(node);
      const source = previous && current === previous.rendered ? previous.source : current;
      const rendered = translate(source, language);
      textRecords.current.set(node, { source, rendered });
      if (current !== rendered) node.nodeValue = rendered;
    };
    const translateAttributes = (element: Element) => {
      if (ignoredTags.has(element.tagName)) return;
      const records = attributeRecords.current.get(element) ?? {};
      for (const name of translatableAttributes) {
        const current = element.getAttribute(name);
        if (!current) continue;
        const previous = records[name];
        const source = previous && current === previous.rendered ? previous.source : current;
        const rendered = translate(source, language);
        records[name] = { source, rendered };
        if (current !== rendered) element.setAttribute(name, rendered);
      }
      attributeRecords.current.set(element, records);
    };
    const translateTree = (root: Node) => {
      if (root.nodeType === Node.TEXT_NODE) translateTextNode(root as Text);
      if (root.nodeType === Node.ELEMENT_NODE) translateAttributes(root as Element);
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
      let current: Node | null = walker.nextNode();
      while (current) {
        if (current.nodeType === Node.TEXT_NODE) translateTextNode(current as Text);
        if (current.nodeType === Node.ELEMENT_NODE) translateAttributes(current as Element);
        current = walker.nextNode();
      }
    };
    const observer = new MutationObserver((changes) => {
      for (const change of changes) {
        if (change.type === 'characterData') translateTextNode(change.target as Text);
        if (change.type === 'attributes') translateAttributes(change.target as Element);
        change.addedNodes.forEach(translateTree);
      }
    });
    translateTree(document.body);
    observer.observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: translatableAttributes });
    return () => observer.disconnect();
  }, [language]);

  return null;
}
