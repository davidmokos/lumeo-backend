import modal
from src.scene_builder import SceneBuilder

app = modal.App(name="learn-anything")
vol = modal.Volume.from_name("learn-anything-vol", create_if_missing=True)

@app.function(volumes={"/data": vol})
def create_python_variables_scene():
    """Example: Creating a scene explaining Python variables."""
    from src.scene_builder import SceneBuilder
    builder = SceneBuilder(app=app, volume=vol)
    
    description = "Introduction to Python Variables"
    voiceover = """Variables in Python are like containers that store data. 
    When we create a variable, Python allocates memory to store its value."""
    details = """
    Create a visual scene that shows:
    1. A container/box representing a variable
    2. Text showing variable name 'x'
    3. An arrow pointing from 'x' to the container
    4. The number 42 appearing inside the container
    5. Text showing 'x = 42' at the bottom
    
    The animation should:
    1. First show the empty container
    2. Then show the variable name
    3. Draw the arrow
    4. Finally show the value 42 appearing inside
    """
    
    result = builder.generate_scene(
        description=description,
        voiceover=voiceover,
        details=details
    )
    
    print(f"\n=== Python Variables Scene ===")
    print(f"Generated after {result['iterations']} iterations")
    print(f"Output video: {result['output_path']}")
    return result

@app.function(volumes={"/data": vol})
def create_sorting_algorithm_scene():
    """Example: Creating a scene explaining bubble sort."""
    from src.scene_builder import SceneBuilder
    builder = SceneBuilder(app=app, volume=vol)
    
    description = "Understanding Bubble Sort Algorithm"
    voiceover = """Bubble sort works by repeatedly stepping through the list, 
    comparing adjacent elements and swapping them if they are in the wrong order."""
    details = """
    Create a visual scene that shows:
    1. An array of 5 numbers: [5, 2, 8, 1, 9]
    2. Highlight pairs being compared in each step
    3. Show swapping animation when needed
    4. Display iteration count
    
    The animation should:
    1. Start with the unsorted array
    2. Highlight each comparison in sequence
    3. Use smooth transitions for swaps
    4. Show the final sorted array
    """
    
    result = builder.generate_scene(
        description=description,
        voiceover=voiceover,
        details=details
    )
    
    print(f"\n=== Bubble Sort Scene ===")
    print(f"Generated after {result['iterations']} iterations")
    print(f"Output video: {result['output_path']}")
    return result

@app.function(volumes={"/data": vol})
def create_binary_tree_scene():
    """Example: Creating a scene explaining binary trees."""
    from src.scene_builder import SceneBuilder
    builder = SceneBuilder(app=app, volume=vol)
    
    description = "Introduction to Binary Trees"
    voiceover = """A binary tree is a hierarchical data structure where each node 
    has at most two children, referred to as left and right child nodes."""
    details = """
    Create a visual scene that shows:
    1. A simple binary tree with root node 10
    2. Left child 5 and right child 15
    3. Add one more level: 3, 7 as children of 5; 12, 18 as children of 15
    
    The animation should:
    1. Start with just the root node
    2. Show left and right children appearing with arrows
    3. Highlight the relationship between parent and child nodes
    4. Label the levels of the tree (root, level 1, level 2)
    """
    
    result = builder.generate_scene(
        description=description,
        voiceover=voiceover,
        details=details
    )
    
    print(f"\n=== Binary Tree Scene ===")
    print(f"Generated after {result['iterations']} iterations")
    print(f"Output video: {result['output_path']}")
    return result

@app.local_entrypoint()
def main():
    """Run all example scenes."""
    print("Generating learning scenes...")
    
    # Generate Python variables scene
    variables_result = create_python_variables_scene.remote()
    print("\nPython Variables Scene Code:")
    print(variables_result['scene_code'])
    
    # Generate bubble sort scene
    sorting_result = create_sorting_algorithm_scene.remote()
    print("\nBubble Sort Scene Code:")
    print(sorting_result['scene_code'])
    
    # Generate binary tree scene
    tree_result = create_binary_tree_scene.remote()
    print("\nBinary Tree Scene Code:")
    print(tree_result['scene_code'])
    
    print("\nAll scenes generated successfully!") 