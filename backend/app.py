from flask import Flask, jsonify, send_from_directory, request, Response, stream_with_context
from flask_cors import CORS
import os
import json
import time

from tools.graph_tools import bfs_find_paths, generate_mechanism_summary, score_repurposing_opportunity
from agents.discovery_agent import run_discovery_agent
from agents.llm_client import LLM_API_KEY, complete

# CML project directory
if os.path.exists('/home/cdsw'):
    PROJECT_DIR = '/home/cdsw'
else:
    PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__, 
            static_folder=os.path.join(PROJECT_DIR, 'frontend/dist'),
            static_url_path='')

CORS(app)

# Load seed graph
SEED_GRAPH_PATH = os.path.join(PROJECT_DIR, 'data/seed_graph.json')
with open(SEED_GRAPH_PATH, 'r') as f:
    SEED_GRAPH = json.load(f)

print(f"✓ Loaded seed graph: {len(SEED_GRAPH['entities'])} entities, {len(SEED_GRAPH['relationships'])} relationships")

# Report token configuration without creating a network client at import time.
if LLM_API_KEY:
    print("✓ LLM API token configured")
else:
    print("⚠️  Warning: no LLM API token configured")


def extract_triplets_with_llm(text: str) -> list:
    """Extract knowledge triplets using the configured LLM provider."""
    
    # Load prompt template
    prompt_path = os.path.join(PROJECT_DIR, 'prompts/extract_triplets.txt')
    with open(prompt_path, 'r') as f:
        prompt_template = f.read()
    
    # Fill in the publication text
    prompt = prompt_template.replace('{PUBLICATION_TEXT}', text)
    
    print("🤖 Calling configured LLM to extract triplets...")
    
    response_text = complete(prompt, max_tokens=4000)
    
    # Remove markdown code fences if present
    response_text = response_text.replace('```json', '').replace('```', '').strip()
    
    # Parse JSON
    triplets = json.loads(response_text)
    
    print(f"✓ Extracted {len(triplets)} triplets")
    
    return triplets

@app.route('/api/hello', methods=['GET'])
def hello():
    """Test endpoint"""
    return jsonify({'message': 'Hello Rameez!'})


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'graph_entities': len(SEED_GRAPH['entities']),
        'graph_relationships': len(SEED_GRAPH['relationships'])
    })


@app.route('/api/graph-data', methods=['GET'])
def get_graph_data():
    """Return graph data in format for react-force-graph"""
    
    # Transform to nodes/links format
    nodes = [
        {
            'id': entity['id'],
            'name': entity['name'],
            'type': entity['type'],
            'group': entity['type'],
            'knowledge_source': entity.get('knowledge_source', 'unknown')
        }
        for entity in SEED_GRAPH['entities']
    ]
    
    links = [
        {
            'source': rel['source'],
            'target': rel['target'],
            'label': rel['relation'],
            'confidence': rel.get('confidence', 0.5)
        }
        for rel in SEED_GRAPH['relationships']
    ]
    
    return jsonify({
        'nodes': nodes,
        'links': links
    })


@app.route('/api/upload-publication', methods=['POST'])
def upload_publication():
    """
    Receive uploaded publication and extract triplets using Claude
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Read file content
        content = file.read().decode('utf-8')
        
        print(f"✓ Received publication: {file.filename} ({len(content)} characters)")
        
        # Extract triplets with Claude
        triplets = extract_triplets_with_llm(content)
        
        return jsonify({
            'success': True,
            'filename': file.filename,
            'content': content,
            'triplets': triplets,
            'triplet_count': len(triplets)
        })
    
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def generate_discovery_stream(question: str):
    """
    Generator function that yields discovery progress events
    """
    try:
        # Step 1: Parse question
        yield f"data: {json.dumps({'step': 'parsing', 'message': '🔍 Analyzing your question...', 'progress': 10})}\n\n"
        time.sleep(0.5)
        
        # Extract entities (hardcoded for demo)
        drug_name = "Semaglutide"
        disease_name = "Obesity"
        
        yield f"data: {json.dumps({'step': 'entities', 'message': f'🎯 Identified: {drug_name} → {disease_name}', 'progress': 20})}\n\n"
        time.sleep(0.5)
        
        # Step 2: Graph search
        yield f"data: {json.dumps({'step': 'searching', 'message': '🧬 Searching knowledge graph...', 'progress': 30})}\n\n"
        
        paths = bfs_find_paths(
            SEED_GRAPH,
            start_entity=drug_name,
            target_entity=disease_name,
            max_depth=10
        )
        
        if not paths:
            yield f"data: {json.dumps({'step': 'error', 'message': 'No paths found', 'progress': 100})}\n\n"
            return
        
        yield f"data: {json.dumps({'step': 'paths_found', 'message': f'📊 Found {len(paths)} possible pathways', 'progress': 50})}\n\n"
        time.sleep(0.5)
        
        top_path = paths[0]
        
        # Step 3: Agent analysis
        yield f"data: {json.dumps({'step': 'agent_analyzing', 'message': '🤖 AI Agent analyzing pathway...', 'progress': 60})}\n\n"
        
        # Prepare path data for agent
        path_data = {
            'nodes': [n['name'] for n in top_path['node_details']],
            'node_types': [n['type'] for n in top_path['node_details']],
            'edges': top_path['edges'],
            'edge_details': top_path['edge_details'],
            'confidence': top_path['confidence'],
            'path_length': top_path['length'],
            'hidden_connections': top_path.get('hidden_connections', 0)
        }
        
        # Run Discovery Agent
        agent_insights = run_discovery_agent(question, path_data)
        
        yield f"data: {json.dumps({'step': 'generating_insights', 'message': '💡 Generating clinical insights...', 'progress': 80})}\n\n"
        time.sleep(0.5)
        
        # Get drug entity and scores
        drug_entity = next(
            (e for e in SEED_GRAPH['entities'] if e['name'] == drug_name),
            {}
        )
        scores = score_repurposing_opportunity(top_path, drug_entity)
        mechanism = generate_mechanism_summary(top_path)
        
        # Build final discovery result
        discovery = {
            'success': True,
            'found_paths': True,
            'drug': agent_insights.get('drug_name', drug_name),
            'disease': agent_insights.get('disease_name', disease_name),
            'top_path': {
                'nodes': [n['name'] for n in top_path['node_details']],
                'node_ids': top_path['nodes'],
                'edges': top_path['edges'],
                'edge_details': top_path['edge_details'],
                'mechanism': mechanism,
                'confidence': top_path['confidence'],
                'path_length': top_path['length'],
                'hidden_connections': top_path.get('hidden_connections', 0)
            },
            'scores': scores,
            'alternative_paths': len(paths),
            
            # Agent-generated insights
            'hypothesis': agent_insights.get('hypothesis'),
            'clinical_significance': agent_insights.get('clinical_significance'),
            'mechanism_explanation': agent_insights.get('mechanism_explanation'),
            'safety_rationale': agent_insights.get('safety_rationale'),
            'knowledge_fragmentation': agent_insights.get('knowledge_fragmentation'),
            'confidence_assessment': agent_insights.get('confidence_assessment'),
            'hidden_knowledge_insight': agent_insights.get('hidden_knowledge_insight'),
            'key_risks': agent_insights.get('key_risks'),
            'next_steps': agent_insights.get('next_steps', []),
            
            # Legacy summary fields
            'mechanism_summary': f"Through {top_path['length']}-step pathway involving " +
                               " → ".join([n['name'] for n in top_path['node_details'][1:-1]]),
            'key_insight': f"Discovery bridges {top_path.get('hidden_connections', 0)} hidden cross-domain connections"
        }
        
        # Final result
        yield f"data: {json.dumps({'step': 'complete', 'message': '✅ Discovery complete!', 'progress': 100, 'result': discovery})}\n\n"
        
    except Exception as e:
        print(f"❌ Discovery error: {e}")
        import traceback
        traceback.print_exc()
        yield f"data: {json.dumps({'step': 'error', 'message': f'Error: {str(e)}', 'progress': 100})}\n\n"


@app.route('/api/discover-stream', methods=['POST'])
def discover_stream():
    """
    Stream discovery progress using Server-Sent Events
    """
    data = request.get_json()
    question = data.get('question', '')
    
    if not question:
        return jsonify({'success': False, 'error': 'No question provided'}), 400
    
    return Response(
        stream_with_context(generate_discovery_stream(question)),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/api/discover', methods=['POST'])
def discover():
    """
    Non-streaming discovery endpoint (for testing/fallback)
    """
    try:
        data = request.get_json()
        question = data.get('question', '')
        
        if not question:
            return jsonify({
                'success': False,
                'error': 'No question provided'
            }), 400
        
        print(f"🔍 Discovery question: {question}")
        
        # Hardcoded entities for demo
        drug_name = "Semaglutide"
        disease_name = "Obesity"
        
        print(f"🎯 Searching: {drug_name} → {disease_name}")
        
        # Find paths using BFS
        paths = bfs_find_paths(
            SEED_GRAPH,
            start_entity=drug_name,
            target_entity=disease_name,
            max_depth=10
        )
        
        if not paths:
            return jsonify({
                'success': True,
                'found_paths': False,
                'message': f'No paths found between {drug_name} and {disease_name}'
            })
        
        # Get top path
        top_path = paths[0]
        
        # Prepare path data for agent
        path_data = {
            'nodes': [n['name'] for n in top_path['node_details']],
            'node_types': [n['type'] for n in top_path['node_details']],
            'edges': top_path['edges'],
            'edge_details': top_path['edge_details'],
            'confidence': top_path['confidence'],
            'path_length': top_path['length'],
            'hidden_connections': top_path.get('hidden_connections', 0)
        }
        
        # Run Discovery Agent
        agent_insights = run_discovery_agent(question, path_data)
        
        # Get drug entity and scores
        drug_entity = next(
            (e for e in SEED_GRAPH['entities'] if e['name'] == drug_name),
            {}
        )
        scores = score_repurposing_opportunity(top_path, drug_entity)
        mechanism = generate_mechanism_summary(top_path)
        
        # Build discovery result
        discovery = {
            'success': True,
            'found_paths': True,
            'drug': agent_insights.get('drug_name', drug_name),
            'disease': agent_insights.get('disease_name', disease_name),
            'top_path': {
                'nodes': [n['name'] for n in top_path['node_details']],
                'node_ids': top_path['nodes'],
                'edges': top_path['edges'],
                'edge_details': top_path['edge_details'],
                'mechanism': mechanism,
                'confidence': top_path['confidence'],
                'path_length': top_path['length'],
                'hidden_connections': top_path.get('hidden_connections', 0)
            },
            'scores': scores,
            'alternative_paths': len(paths),
            
            # Agent-generated insights
            'hypothesis': agent_insights.get('hypothesis'),
            'clinical_significance': agent_insights.get('clinical_significance'),
            'mechanism_explanation': agent_insights.get('mechanism_explanation'),
            'safety_rationale': agent_insights.get('safety_rationale'),
            'knowledge_fragmentation': agent_insights.get('knowledge_fragmentation'),
            'confidence_assessment': agent_insights.get('confidence_assessment'),
            'hidden_knowledge_insight': agent_insights.get('hidden_knowledge_insight'),
            'key_risks': agent_insights.get('key_risks'),
            'next_steps': agent_insights.get('next_steps', []),
            
            # Legacy summary fields
            'mechanism_summary': f"Through {top_path['length']}-step pathway involving " +
                               " → ".join([n['name'] for n in top_path['node_details'][1:-1]]),
            'key_insight': f"Discovery bridges {top_path.get('hidden_connections', 0)} hidden cross-domain connections"
        }
        
        print(f"✓ Discovery complete: {len(paths)} paths found")
        print(f"  Top path: {top_path['length']} hops, {top_path['confidence']:.0%} confidence")
        
        return jsonify(discovery)
    
    except Exception as e:
        print(f"❌ Discovery error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Serve React frontend
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """Serve the React frontend"""
    static_dir = os.path.join(PROJECT_DIR, 'frontend/dist')
    if path and os.path.exists(os.path.join(static_dir, path)):
        return send_from_directory(static_dir, path)
    return send_from_directory(static_dir, 'index.html')


if __name__ == '__main__':
    port = int(os.environ.get('CDSW_APP_PORT', 8080))
    app.run(host='127.0.0.1', port=port, debug=False, threaded=True)
