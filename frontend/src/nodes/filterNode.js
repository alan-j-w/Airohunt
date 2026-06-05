import React from "react";
import BaseNode from "../components/BaseNode";
import { useStore } from "../store";

const FilterNode = ({ id, data }) => {
  const updateNodeField = useStore((state) => state.updateNodeField);
  
  const currency = data?.currency || "INR_LPA";
  const salaryUnknownPolicy = data?.salaryUnknownPolicy || "Allow";
  const minSalary = data?.minSalary !== undefined ? data.minSalary : (currency === "INR_LPA" ? 3 : 60000);
  const jobType = data?.jobType || "Full-Time";

  const handleCurrencyChange = (e) => {
    const nextCurrency = e.target.value;
    updateNodeField(id, "currency", nextCurrency);
    if (nextCurrency === "INR_LPA") {
      updateNodeField(id, "minSalary", 3);
    } else {
      updateNodeField(id, "minSalary", 60000);
    }
  };

  const isINR = currency === "INR_LPA";
  const minVal = isINR ? 1 : 10000;
  const maxVal = isINR ? 25 : 200000;
  const stepVal = isINR ? 0.5 : 5000;

  const formattedSalary = isINR 
    ? `${minSalary} LPA` 
    : `$${Number(minSalary).toLocaleString()}`;

  return (
    <BaseNode
      title="Salary & Type Filter"
      inputs={[{ id: "jobs_in", label: "Jobs In" }]}
      outputs={[{ id: "jobs_out", label: "Filtered" }]}
      headerBg="bg-amber-500"
      headerTextColor="text-black"
      borderColor="border-amber-500/40"
    >
      <div className="space-y-3 text-xs">
        <div>
          <label className="text-slate-400 font-bold block mb-1">Currency</label>
          <select
            value={currency}
            onChange={handleCurrencyChange}
            className="w-full p-1.5 rounded bg-slate-950 text-white border border-slate-800 focus:outline-none focus:border-amber-500 cursor-pointer"
          >
            <option value="INR_LPA">INR (Lakhs Per Annum)</option>
            <option value="USD">USD (Annual)</option>
          </select>
        </div>

        <div>
          <label className="text-slate-400 font-bold block mb-1">
            Min Salary: <span className="text-amber-400">{formattedSalary}</span>
          </label>
          <input
            type="range"
            min={minVal}
            max={maxVal}
            step={stepVal}
            value={minSalary}
            onChange={(e) => updateNodeField(id, "minSalary", Number(e.target.value))}
            className="w-full h-1 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-amber-500"
          />
        </div>

        <div>
          <label className="text-slate-400 font-bold block mb-1">Salary Missing Policy</label>
          <select
            value={salaryUnknownPolicy}
            onChange={(e) => updateNodeField(id, "salaryUnknownPolicy", e.target.value)}
            className="w-full p-1.5 rounded bg-slate-950 text-white border border-slate-800 focus:outline-none focus:border-amber-500 cursor-pointer"
          >
            <option value="Allow">Allow (Show Jobs)</option>
            <option value="Warn">Warn (Show + Badge)</option>
            <option value="Hide">Hide (Discard Jobs)</option>
          </select>
        </div>

        <div>
          <label className="text-slate-400 font-bold block mb-1">Job Type</label>
          <select
            value={jobType}
            onChange={(e) => updateNodeField(id, "jobType", e.target.value)}
            className="w-full p-1.5 rounded bg-slate-950 text-white border border-slate-800 focus:outline-none focus:border-amber-500 cursor-pointer"
          >
            <option value="Full-Time">Full-Time</option>
            <option value="Part-Time">Part-Time</option>
            <option value="Internship">Internship</option>
            <option value="Contract">Contract</option>
          </select>
        </div>
      </div>
    </BaseNode>
  );
};

export default FilterNode;

