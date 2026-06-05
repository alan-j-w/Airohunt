import { useState, useRef, useCallback, useEffect } from 'react';
import ReactFlow, {
  Controls,
  Background,
  MiniMap
} from 'reactflow';
import { shallow } from 'zustand/shallow';
import { useStore } from './store';

import TriggerNode from './nodes/triggerNode';
import FilterNode from './nodes/filterNode';
import ScamFilterNode from './nodes/scamFilterNode';
import SkillMatchNode from './nodes/skillMatchNode';
import ScoreNode from './nodes/scoreNode';
import TailorNode from './nodes/tailorNode';
import ApplyNode from './nodes/applyNode';
import PreferenceNode from './nodes/preferenceNode';
import OpportunityRankerNode from './nodes/opportunityRankerNode';
import SourcesNode from './nodes/sourcesNode';

import 'reactflow/dist/style.css';

const gridSize = 20;

const proOptions = {
  hideAttribution: true
};

const nodeTypes = {
  jobSearchTrigger: TriggerNode,
  jobSources: SourcesNode,
  preferenceFilter: PreferenceNode,
  salaryFilter: FilterNode,
  scamFilter: ScamFilterNode,
  skillMatch: SkillMatchNode,
  opportunityRanker: OpportunityRankerNode,
  resumeScore: ScoreNode,
  resumeTailor: TailorNode,
  appSubmit: ApplyNode,
};

const selector = (state) => ({
  nodes: state.nodes,
  edges: state.edges,
  getNodeID: state.getNodeID,
  addNode: state.addNode,
  onNodesChange: state.onNodesChange,
  onEdgesChange: state.onEdgesChange,
  onConnect: state.onConnect,
  setNodesAndEdges: state.setNodesAndEdges,
  savePipeline: state.savePipeline,
});

export const PipelineUI = () => {
  const reactFlowWrapper = useRef(null);
  const [reactFlowInstance, setReactFlowInstance] = useState(null);

  const {
    nodes,
    edges,
    getNodeID,
    addNode,
    onNodesChange,
    onEdgesChange,
    onConnect,
    setNodesAndEdges,
    savePipeline
  } = useStore(selector, shallow);

  // Load default template if the pipeline is empty (Highly visual developer onboarding helper)
  useEffect(() => {
    if (nodes.length === 0) {
      const defaultNodes = [
        {
          id: "jobSearchTrigger-1",
          type: "jobSearchTrigger",
          position: { x: 50, y: 150 },
          data: { id: "jobSearchTrigger-1", keywords: "Software Engineer", location: "Remote" }
        },
        {
          id: "jobSources-1",
          type: "jobSources",
          position: { x: 320, y: 150 },
          data: { id: "jobSources-1", sourceAdzuna: true, sourceJooble: true, sourceManualImport: false, sourceCompanyCareers: true }
        },
        {
          id: "preferenceFilter-1",
          type: "preferenceFilter",
          position: { x: 590, y: 150 },
          data: { id: "preferenceFilter-1", aiInstructions: "" }
        },
        {
          id: "salaryFilter-1",
          type: "salaryFilter",
          position: { x: 860, y: 150 },
          data: { id: "salaryFilter-1", minSalary: 3, currency: "INR_LPA", salaryUnknownPolicy: "Allow", jobType: "Full-Time" }
        },
        {
          id: "scamFilter-1",
          type: "scamFilter",
          position: { x: 1130, y: 150 },
          data: { id: "scamFilter-1", scamMode: "balanced" }
        },
        {
          id: "skillMatch-1",
          type: "skillMatch",
          position: { x: 1400, y: 150 },
          data: { id: "skillMatch-1", minMatchPercent: 50 }
        },
        {
          id: "opportunityRanker-1",
          type: "opportunityRanker",
          position: { x: 1670, y: 150 },
          data: { id: "opportunityRanker-1", startupWeight: "Medium", remoteWeight: "Medium", salaryWeight: "Medium", trustWeight: "Medium" }
        },
        {
          id: "resumeScore-1",
          type: "resumeScore",
          position: { x: 1940, y: 150 },
          data: { id: "resumeScore-1" }
        },
        {
          id: "resumeTailor-1",
          type: "resumeTailor",
          position: { x: 2210, y: 150 },
          data: { id: "resumeTailor-1", modelType: "local" }
        },
        {
          id: "appSubmit-1",
          type: "appSubmit",
          position: { x: 2480, y: 150 },
          data: { id: "appSubmit-1", automationMode: "Assisted Apply" }
        }
      ];

      const defaultEdges = [
        {
          id: "e-trigger-sources",
          source: "jobSearchTrigger-1",
          target: "jobSources-1",
          type: "smoothstep",
          animated: true,
          style: { stroke: "#06b6d4", strokeWidth: 2 }
        },
        {
          id: "e-sources-pref",
          source: "jobSources-1",
          target: "preferenceFilter-1",
          type: "smoothstep",
          animated: true,
          style: { stroke: "#06b6d4", strokeWidth: 2 }
        },
        {
          id: "e-pref-sal",
          source: "preferenceFilter-1",
          target: "salaryFilter-1",
          type: "smoothstep",
          animated: true,
          style: { stroke: "#06b6d4", strokeWidth: 2 }
        },
        {
          id: "e-sal-scam",
          source: "salaryFilter-1",
          target: "scamFilter-1",
          type: "smoothstep",
          animated: true,
          style: { stroke: "#06b6d4", strokeWidth: 2 }
        },
        {
          id: "e-scam-skill",
          source: "scamFilter-1",
          target: "skillMatch-1",
          type: "smoothstep",
          animated: true,
          style: { stroke: "#06b6d4", strokeWidth: 2 }
        },
        {
          id: "e-skill-ranker",
          source: "skillMatch-1",
          target: "opportunityRanker-1",
          type: "smoothstep",
          animated: true,
          style: { stroke: "#06b6d4", strokeWidth: 2 }
        },
        {
          id: "e-ranker-score",
          source: "opportunityRanker-1",
          target: "resumeScore-1",
          type: "smoothstep",
          animated: true,
          style: { stroke: "#06b6d4", strokeWidth: 2 }
        },
        {
          id: "e-score-tailor",
          source: "resumeScore-1",
          target: "resumeTailor-1",
          type: "smoothstep",
          animated: true,
          style: { stroke: "#06b6d4", strokeWidth: 2 }
        },
        {
          id: "e-tailor-apply",
          source: "resumeTailor-1",
          target: "appSubmit-1",
          type: "smoothstep",
          animated: true,
          style: { stroke: "#06b6d4", strokeWidth: 2 }
        }
      ];

      setNodesAndEdges(defaultNodes, defaultEdges);
      // Save template to backend persistence
      setTimeout(() => savePipeline(), 500);
    }
  }, [nodes, setNodesAndEdges, savePipeline]);

  const getInitNodeData = (nodeID, type) => {
    return {
      id: nodeID,
      nodeType: type,
    };
  };

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();

      const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
      const data = event.dataTransfer.getData('application/reactflow');

      if (!data) return;

      const appData = JSON.parse(data);
      const type = appData?.nodeType;

      if (!type) return;

      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });

      const nodeID = getNodeID(type);

      const newNode = {
        id: nodeID,
        type,
        position,
        data: getInitNodeData(nodeID, type),
      };

      addNode(newNode);
    },
    [reactFlowInstance, addNode, getNodeID]
  );

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  return (
    <div
      ref={reactFlowWrapper}
      style={{
        width: '100%',
        height: 'calc(100vh - 190px)',
        background: '#020617'
      }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onInit={setReactFlowInstance}
        nodeTypes={nodeTypes}
        proOptions={proOptions}
        snapToGrid={true}
        snapGrid={[gridSize, gridSize]}
        fitView
      >
        <Background color="#1e293b" gap={20} />
        <Controls />
        <MiniMap 
          nodeColor={(n) => {
            if (n.type === 'jobSearchTrigger') return '#06b6d4';
            if (n.type === 'scamFilter') return '#f43f5e';
            if (n.type === 'skillMatch') return '#10b981';
            return '#6366f1';
          }}
          maskColor="rgba(15, 23, 42, 0.6)"
          style={{ background: '#0f172a', border: '1px solid #1e293b' }}
        />
      </ReactFlow>
    </div>
  );
};
export default PipelineUI;