import os
import zlib
import xml.etree.ElementTree as ET
from hashlib import sha1
from datetime import datetime
from typing import List, Dict, Tuple

def load_config_from_xml(config_path: str) -> Dict[str, str]:
    """Загрузить конфигурацию из XML файла и преобразовать дату коммита в формат datetime."""
    tree = ET.parse(config_path)
    root = tree.getroot()
    
    # Загружаем конфигурацию и преобразуем дату коммита в datetime
    config = {
        "visualization_tool": root.find('visualization_tool').text,
        "repository_path": root.find('repository_path').text,
        "output_image_path": root.find('output_image_path').text,
        "commit_dates": datetime.strptime(root.find('commit_dates').text, '%Y-%m-%d %H:%M:%S'),
        "tag_names": [tag.text for tag in root.find('tag_names').findall('tag')]
    }
    return config

def read_git_object(repo_path: str, object_hash: str) -> str:
    """Читать объект Git и возвращать его содержимое как строку."""
    object_path = os.path.join(repo_path, '.git', 'objects', object_hash[:2], object_hash[2:])
    try:
        with open(object_path, 'rb') as f:
            compressed_contents = f.read()
            decompressed_contents = zlib.decompress(compressed_contents)
            return decompressed_contents.decode('utf-8')
    except FileNotFoundError:
        raise Exception(f"Object {object_hash} not found.")
    except Exception as e:
        raise Exception(f"Error reading object {object_hash}: {str(e)}")

def get_commit_data(repo_path: str, commit_hash: str) -> Tuple[str, str, str, str]:
    """Получить данные коммита: хеш, дата, автор, сообщение."""
    commit_data = read_git_object(repo_path, commit_hash)
    lines = commit_data.splitlines()
    author = ""
    date = ""
    message = []
    reading_message = False
    
    for line in lines:
        if line.startswith("author "):
            author_info = line.split("author ")[1]
            author_name = author_info.rsplit(' ', 2)[0]
            timestamp = author_info.rsplit(' ', 2)[1]

            # Преобразуем временную метку в читаемый формат даты
            date = datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
            author = author_name
        elif not line:
            reading_message = True
        elif reading_message:
            message.append(line)
    
    return commit_hash, date, author, "\n".join(message)

def get_tag_commit(repo_path: str, tag_name: str) -> str:
    """Получить хеш коммита, связанный с указанным тегом."""
    tag_path = os.path.join(repo_path, '.git', 'refs', 'tags', tag_name)
    try:
        with open(tag_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        raise Exception(f"Tag {tag_name} not found.")

def get_commits_between(repo_path: str, start_hash: str, min_date: datetime, end_hash: str = None) -> List[Tuple[str, str, str, str]]:
    """Получить список коммитов между двумя хешами, фильтруя по дате."""
    commits = []
    current_hash = start_hash

    while current_hash:
        commit_hash, commit_date, commit_author, commit_message = get_commit_data(repo_path, current_hash)
        
        # Преобразуем дату коммита в объект datetime и проверяем, соответствует ли она минимальной дате
        commit_datetime = datetime.strptime(commit_date, '%Y-%m-%d %H:%M:%S')
        if commit_datetime >= min_date:
            commits.append((commit_hash, commit_date, commit_author, commit_message))
        
        # Получаем родительский коммит
        commit_content = read_git_object(repo_path, current_hash)
        parent_line = next((line for line in commit_content.splitlines() if line.startswith("parent ")), None)
        
        if parent_line:
            current_hash = parent_line.split(" ")[1]
            if current_hash == end_hash:
                break
        else:
            break

    return commits[::-1]  # Возвращаем список в прямом порядке

def get_commits_for_tags(repo_path: str, tag_names: List[str], min_date: datetime) -> Dict[str, List[Tuple[str, str, str, str]]]:
    """Получить коммиты для всех указанных тегов с фильтрацией по дате."""
    commits_per_tag = {}
    previous_commit = None
    for tag_name in tag_names:
        tag_commit = get_tag_commit(repo_path, tag_name)
        commits = get_commits_between(repo_path, tag_commit, min_date, previous_commit)
        commits_per_tag[tag_name] = commits
        previous_commit = tag_commit
    return commits_per_tag

def build_plantuml_graph(commits_per_tag: Dict[str, List[Tuple[str, str, str, str]]]) -> str:
    """Создать граф в формате PlantUML из коммитов, используя только хеши в узлах."""
    plantuml_code = '@startuml\n'
    for tag, commits in commits_per_tag.items():
        plantuml_code += f'package "{tag}" {{\n'
        for idx, (commit_hash, _, _, _) in enumerate(commits):
            # Отображаем только хеш коммита в каждом узле
            plantuml_code += f'node "{commit_hash}" as {tag}_{idx}\n'
        for i in range(len(commits) - 1):
            plantuml_code += f'{tag}_{i} --> {tag}_{i + 1}\n'
        plantuml_code += '}\n'
    plantuml_code += '@enduml'
    return plantuml_code

def visualize_graph(plantuml_code: str, visualization_tool: str, output_image_path: str):
    """Сохранить граф в файл и визуализировать его с помощью PlantUML."""
    with open("graph.puml", "w") as f:
        f.write(plantuml_code)

    command = f"java -jar \"{visualization_tool}\" -tpng graph.puml -o \"{output_image_path}\""
    print(f"Executing command: {command}")  # Отладочная информация
    result = os.system(command)

    if result != 0:
        raise Exception("Error visualizing graph. Please check the command and PlantUML setup.")
    else:
        print(f"PNG file successfully created at {output_image_path}!")
    os.remove("graph.puml")

def main(config_path: str):
    """Основная функция для загрузки конфигурации, получения коммитов и визуализации графа."""
    config = load_config_from_xml(config_path)
    print("Loaded config:", config)  # Отладочная информация
    
    commits_per_tag = get_commits_for_tags(config['repository_path'], config['tag_names'], config['commit_dates'])
    print(f"Commits found: {commits_per_tag}")  # Отладочная информация
    
    plantuml_code = build_plantuml_graph(commits_per_tag)
    visualize_graph(plantuml_code, config['visualization_tool'], config['output_image_path'])

if __name__ == "__main__":
    main("config.xml")
