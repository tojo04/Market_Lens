import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { searchCompanies } from "../api/companies";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import type { CompanyMatch } from "../types/market";

interface CompanySearchProps {
  selectedCompany: CompanyMatch | null;
  onSelect: (company: CompanyMatch) => void;
}

export function CompanySearch({ selectedCompany, onSelect }: CompanySearchProps) {
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebouncedValue(query.trim(), 300);
  const searchQuery = useQuery({
    queryKey: ["companies", debouncedQuery],
    queryFn: ({ signal }) => searchCompanies(debouncedQuery, signal),
    enabled: debouncedQuery.length > 0,
    staleTime: 5 * 60 * 1000,
  });

  return (
    <section className="panel" aria-labelledby="company-search-title">
      <div className="step-label">Step 1</div>
      <h2 id="company-search-title">Find a listed company</h2>
      <p className="muted">Search the small supported-company directory to begin.</p>
      <label htmlFor="company-query">Company name, BSE code, or NSE symbol</label>
      <input
        id="company-query"
        type="search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Try Infosys, 500209, or INFY"
        autoComplete="off"
      />

      {searchQuery.isFetching && (
        <p className="inline-status muted" role="status">
          <span className="spinner spinner-small" aria-hidden="true" />
          Searching supported companies…
        </p>
      )}
      {searchQuery.isError && (
        <p className="error" role="alert">Company search is temporarily unavailable.</p>
      )}
      {searchQuery.data?.items.length === 0 && <p className="muted">No supported company matched.</p>}

      {searchQuery.data && searchQuery.data.items.length > 0 && (
        <ul className="result-list" aria-label="Company search results">
          {searchQuery.data.items.map((company) => {
            const isSelected = selectedCompany?.company_id === company.company_id;
            return (
              <li key={company.company_id}>
                <button
                  type="button"
                  className={isSelected ? "result-button selected" : "result-button"}
                  onClick={() => onSelect(company)}
                  aria-pressed={isSelected}
                >
                  <span>{company.company_name}</span>
                  <small>
                    {company.symbol ?? "No NSE symbol"} · BSE {company.security_code ?? "—"} · {company.exchange}
                  </small>
                </button>
              </li>
            );
          })}
        </ul>
      )}

      {selectedCompany && (
        <p className="selection" role="status">
          Selected: <strong>{selectedCompany.company_name}</strong>
        </p>
      )}
    </section>
  );
}
