import React from "react";
import BaseNode from "../components/BaseNode";

const ScoreNode = () => {
  return (
    <BaseNode
      title="Resume Scorer"
      inputs={[{ id: "jobs_in", label: "Jobs In" }]}
      outputs={[{ id: "jobs_out", label: "Scored" }]}
      headerBg="bg-indigo-500"
      borderColor="border-indigo-500/40"
    >
      <div className="text-[10px] text-slate-400 leading-normal space-y-1.5">
        <p>
          Calculates keyword relevance score between candidate resume profile and active job descriptions.
        </p>
        <div className="px-2 py-1 bg-slate-950 border border-slate-800 rounded font-semibold text-slate-300">
          Metric: Tf-Idf Overlap
        </div>
      </div>
    </BaseNode>
  );
};

export default ScoreNode;
