import { useEffect, useId, useState } from "react";
import { wholesalePartyApi } from "../api/endpoints";

export default function PartyCombobox({ value, onChange, label = "Party", activeOnly = true }) {
  const listId = useId();
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(null);
  const [options, setOptions] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [searchError, setSearchError] = useState("");

  useEffect(() => {
    if (!value) {
      setSelected(null);
      setQuery("");
      return;
    }
    if (selected?.id === Number(value)) return;
    wholesalePartyApi.get(value)
      .then(({ data: party }) => {
        setSelected(party);
        setQuery(party.name);
      })
      .catch((error) => setSearchError(apiErrorMessage(error, `Party detail API (/wholesale/parties/${value}/)`)));
  }, [value]);

  useEffect(() => {
    if (!open) return undefined;
    const timer = window.setTimeout(() => {
      setLoading(true);
      setSearchError("");
      wholesalePartyApi.list({ search: query, ...(activeOnly ? { is_active: true } : {}), page_size: 10 })
        .then(({ data }) => setOptions(data.results || data))
        .catch((error) => {
          setOptions([]);
          setSearchError(apiErrorMessage(error, "Party list API (/wholesale/parties/)"));
        })
        .finally(() => setLoading(false));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [query, open, activeOnly]);

  function choose(party) {
    setSelected(party);
    setQuery(party.name);
    setOpen(false);
    setActiveIndex(-1);
    onChange(String(party.id), party);
  }

  function handleKeyDown(event) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
      setActiveIndex((index) => Math.min(index + 1, options.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((index) => Math.max(index - 1, 0));
    } else if (event.key === "Enter" && open && activeIndex >= 0 && options[activeIndex]) {
      event.preventDefault();
      choose(options[activeIndex]);
    } else if (event.key === "Escape") {
      setOpen(false);
      setQuery(selected?.name || "");
    }
  }

  return (
    <div className="relative">
      <label htmlFor={`${listId}-input`} className="mb-1 block text-xs text-gray-500">{label}</label>
      <input
        id={`${listId}-input`}
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={open}
        aria-controls={listId}
        aria-activedescendant={activeIndex >= 0 ? `${listId}-option-${activeIndex}` : undefined}
        autoComplete="off"
        value={query}
        onFocus={() => setOpen(true)}
        onBlur={() => window.setTimeout(() => setOpen(false), 120)}
        onChange={(event) => {
          setQuery(event.target.value);
          setOpen(true);
          setActiveIndex(-1);
          if (selected) {
            setSelected(null);
            onChange("", null);
          }
        }}
        onKeyDown={handleKeyDown}
        placeholder="Type a party name or phone"
        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900"
      />
      {open && <ul id={listId} role="listbox" className="absolute z-30 mt-1 max-h-56 w-full overflow-auto rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
        {loading && <li className="px-3 py-2 text-sm text-gray-500">Searching...</li>}
        {!loading && options.map((party, index) => <li
          id={`${listId}-option-${index}`}
          key={party.id}
          role="option"
          aria-selected={activeIndex === index}
          onMouseDown={(event) => event.preventDefault()}
          onClick={() => choose(party)}
          className={`cursor-pointer px-3 py-2 text-sm ${activeIndex === index ? "bg-gray-100" : "hover:bg-gray-50"}`}
        >{party.name}{party.phone ? <span className="ml-2 text-xs text-gray-500">{party.phone}</span> : null}</li>)}
          {!loading && searchError && <li role="alert" className="px-3 py-2 text-sm text-red-700">{searchError}</li>}
        {!loading && !options.length && !searchError && <li className="px-3 py-2 text-sm text-gray-500">No matching parties</li>}
      </ul>}
    </div>
  );
}

function apiErrorMessage(error, endpoint) {
  const status = error.response?.status;
  const body = error.response?.data;
  if (status === 404) return `${endpoint} returned 404. Verify the frontend API base URL and backend deployment.`;
  if (status === 401 || status === 403) return `${endpoint} returned ${status}. Sign in with an authorized Admin account.`;
  if (status >= 500) return `${endpoint} returned ${status}. Check the backend error logs.`;
  if (!body) return `${endpoint} could not be reached. Check the API base URL and network connection.`;
  return `${endpoint}: ${body.detail || "Request failed."}${status ? ` (HTTP ${status})` : ""}`;
}