import React from "react";
import BaseNode from "../components/BaseNode";
import { useStore } from "../store";

const LLMNode = ({ id, data }) => {
  const updateNodeField = useStore((state) => state.updateNodeField);
  const value = data?.model || "GPT-4";

  return (
    <BaseNode
      title="LLM Node"
      inputs={[{ id: "prompt" }]}
      outputs={[{ id: "response" }]}
    >
      <select
        value={value}
        onChange={(e) => {
          if (id) {
            updateNodeField(id, "model", e.target.value);
          }
        }}
        className="w-full p-2 rounded bg-slate-800 text-white border border-slate-700 focus:outline-none focus:border-cyan-500 transition-colors"
      >
        <option value="GPT-4">GPT-4</option>
        <option value="Claude">Claude</option>
      </select>
    </BaseNode>
  );
};

export default LLMNode;