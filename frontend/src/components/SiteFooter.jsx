export function SiteFooter() {
  return (
    <footer className="border-t border-gray-200/80 px-4 py-3 text-center text-xs text-gray-500 dark:border-slate-700 dark:text-slate-400">
      Copyright reserved MHRobin
    </footer>
  );
}

export function WhatsAppButton() {
  return (
    <a
      href="https://wa.me/8801781879276"
      target="_blank"
      rel="noreferrer"
      aria-label="Message MHRobin on WhatsApp"
      title="Message us on WhatsApp"
      className="fixed bottom-5 right-5 z-50 flex h-12 w-12 items-center justify-center rounded-full bg-[#25D366] text-white shadow-lg transition-transform hover:scale-105 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-green-300"
    >
      <svg viewBox="0 0 32 32" aria-hidden="true" className="h-7 w-7" fill="currentColor">
        <path d="M16.04 3C8.87 3 3.04 8.78 3.04 15.9c0 2.28.6 4.5 1.75 6.45L3 29l6.85-1.78a13.1 13.1 0 0 0 6.18 1.56h.01c7.16 0 13-5.79 13-12.9 0-3.45-1.36-6.69-3.83-9.13A12.9 12.9 0 0 0 16.04 3Zm0 23.6h-.01c-1.9 0-3.77-.5-5.4-1.46l-.39-.23-4.06 1.05 1.08-3.93-.25-.4a10.6 10.6 0 0 1-1.63-5.73c0-5.84 4.79-10.6 10.67-10.6 2.84 0 5.52 1.1 7.53 3.1a10.5 10.5 0 0 1 3.13 7.5c0 5.84-4.79 10.6-10.67 10.6Zm5.86-7.94c-.32-.16-1.9-.93-2.2-1.03-.3-.11-.51-.16-.73.16-.21.32-.83 1.03-1.02 1.24-.19.22-.38.24-.7.08-.32-.16-1.35-.5-2.57-1.59-.95-.84-1.6-1.87-1.79-2.19-.19-.32-.02-.49.14-.65.15-.15.32-.38.49-.57.16-.19.21-.32.32-.54.11-.21.05-.4-.03-.56-.08-.16-.73-1.73-1-2.37-.26-.62-.53-.54-.73-.55h-.62c-.21 0-.56.08-.86.4-.3.32-1.13 1.1-1.13 2.67s1.16 3.1 1.32 3.31c.16.21 2.28 3.46 5.52 4.85.77.33 1.37.53 1.84.68.77.24 1.47.21 2.02.13.62-.09 1.9-.78 2.17-1.53.27-.76.27-1.41.19-1.54-.08-.13-.29-.21-.62-.37Z" />
      </svg>
    </a>
  );
}
