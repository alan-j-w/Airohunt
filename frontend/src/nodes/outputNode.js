import React from "react";
import BaseNode from "../components/BaseNode";

const OutputNode = () => {
  return (
    <BaseNode
      title="Output Node"
      inputs={[{ id: "input" }]}
    >
      <div className="text-sm">
        Output Preview
      </div>
    </BaseNode>
  );
};

export default OutputNode;