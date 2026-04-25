from langgraph.graph import StateGraph, END
from pipeline.state import PipelineState
from pipeline.profiler import profile_data
from pipeline.bias_detector import detect_bias
from pipeline.explainer import explain_findings

def build_audit_pipeline():
    graph = StateGraph(PipelineState)
    graph.add_node("profiler", profile_data)
    graph.add_node("bias_detector", detect_bias)
    graph.add_node("explainer", explain_findings)
    graph.add_edge("profiler", "bias_detector")
    graph.add_edge("bias_detector", "explainer")
    graph.add_edge("explainer", END)
    graph.set_entry_point("profiler")
    return graph.compile()

audit_pipeline = build_audit_pipeline()
