import React from "react";
import BaseNode from "../components/BaseNode";
import { useStore } from "../store";

const InputNode = ({ id, data }) => {
  const updateNodeField = useStore((state) => state.updateNodeField);
  const value = data?.inputValue || "";

  return (
    <BaseNode
      title="Input Node"
      outputs={[{ id: "value" }]}
    >
      <input
        value={value}
        onChange={(e) => {
          if (id) {
            updateNodeField(id, "inputValue", e.target.value);
          }
        }}
        className="w-full p-2 rounded bg-slate-800 text-white border border-slate-700 focus:outline-none focus:border-cyan-500 transition-colors"
        placeholder="Input value"
      />
    </BaseNode>
  );
};

export default InputNode;