#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import io
#  UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

"""
third1.py - 1 name_filtering_rules.txt 2 3 
"""

import csv
import os
import time
import subprocess
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

class ThirdChecker1:
    """从name_filtering_rules.txt取得分类与关键词的检查器"""
    
    def __init__(self):
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
    
    def load_template_categories(self) -> Dict[str, List[str]]:
        """步骤1: 从name_filtering_rules.txt取得分类与关键词"""
        template_file = Path("name_filtering_rules.txt")
        
        if not template_file.exists():
            print(f"Template file not found: {template_file}")
            return {}
        
        categories = {}
        
        with open(template_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        current_category = None
        current_keywords = []
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            
            if '#genre#' in line:
                # 保存前一个分类
                if current_category:
                    categories[current_category] = current_keywords
                
                # 开始新分类
                current_category = line.split('#genre#')[0].strip()
                current_keywords = []
                print(f"  : {current_category}")
                
            elif current_category and line:
                # 
                current_keywords.append(line)
                print(f"   : {line}")
        
        # 保存最后一个分类
        if current_category:
            categories[current_category] = current_keywords
        
        print(f"\n 成功读取 {len(categories)} 个分类")
        return categories
    
    def classify_step6_resources(self, categories: Dict[str, List[str]]) -> Dict[str, List[Dict[str, Any]]]:
        """步骤2: 进行分类操作"""
        step6_file = Path("output/step6_video_resources.csv")
        
        if not step6_file.exists():
            print(f"❌ Step6文件不存在：{step6_file}")
            return {}
        
        # 读取Step6资源
        resources = []
        try:
            with open(step6_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        name = row[0].strip()
                        url = row[1].strip()
                        if name and url and url.startswith('http'):
                            resources.append({
                                'name': name,
                                'url': url,
                                'category': '未分类'
                            })
        except Exception as e:
            print(f"❌ 读取Step6文件失败：{e}")
            return {}
        
        print(f"  读取到 {len(resources)} 个Step6资源")
        
        # 按分类进行分类
        classified_resources = {}
        used_resources = set()
        
        for category_name, keywords in categories.items():
            classified_resources[category_name] = []
            
            for resource in resources:
                resource_id = (resource['name'], resource['url'])
                
                if resource_id not in used_resources:
                    # 检查资源是否匹配该分类的任何关键词
                    for keyword in keywords:
                        if keyword.lower() in resource['name'].lower():
                            classified_resources[category_name].append(resource)
                            used_resources.add(resource_id)
                            break  # 匹配到一个关键词就停止
        
        # 统计分类结果
        total_classified = sum(len(resources) for resources in classified_resources.values())
        print(f"\n  :")
        for category_name, resources in classified_resources.items():
            print(f"  {category_name}: {len(resources)} ")
        
        unclassified_count = len(resources) - len(used_resources)
        print(f"  : {unclassified_count} ")
        print(f"  : {total_classified} ")
        
        return classified_resources
    
    def generate_classified_files(self, classified_resources: Dict[str, List[Dict[str, Any]]]):
        """步骤3: 后续步骤 - 生成分类文件"""
        print(f"\n  ...")
        
        for category_name, resources in classified_resources.items():
            if not resources:
                continue
                
            # 
            filename = f"output/{category_name.replace(' ', '').replace(' ', '').replace(' ', '').replace(' ', '').replace(' ', '')}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                for resource in resources:
                    f.write(f"{resource['name']},{resource['url']}\n")
            
            print(f"  : {filename} ({len(resources)} )")
        
        # 
        with open("output/classification_summary.txt", 'w', encoding='utf-8') as f:
            f.write(" \n")
            f.write("=" * 50 + "\n")
            
            total_resources = sum(len(resources) for resources in classified_resources.values())
            
            for category_name, resources in classified_resources.items():
                f.write(f"{category_name}: {len(resources)} \n")
                for resource in resources[:5]:  # 
                    f.write(f"  - {resource['name']}\n")
                if len(resources) > 5:
                    f.write(f"  ...  {len(resources) - 5} \n")
                f.write("\n")
            
            f.write(f": {total_resources} \n")
        
        print(f"  : output/classification_summary.txt")
    
    def run(self):
        """ """
        print("=" * 80)
        print("  -  name_filtering_rules.txt ")
        print("=" * 80)
        
        #  1:  name_filtering_rules.txt 
        print(f"\n  1:  name_filtering_rules.txt ")
        categories = self.load_template_categories()
        
        if not categories:
            print("  , ")
            return
        
        #  2:  
        print(f"\n  2: ")
        classified_resources = self.classify_step6_resources(categories)
        
        #  3:  
        print(f"\n  3: ")
        self.generate_classified_files(classified_resources)
        
        print(f"\n !")
    
    def _load_whitelist_resources(self) -> List[Dict[str, Any]]:
        """  5MB/s"""
        whitelist_file = Path("white.txt")
        whitelist_resources = []
        
        if not whitelist_file.exists():
            print(f"  : {whitelist_file}")
            return whitelist_resources
        
        try:
            with open(whitelist_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if ',' in line:
                        parts = line.split(',', 1)
                        if len(parts) >= 2:
                            name = parts[0].strip()
                            url = parts[1].strip()
                            
                            if name and url and url.startswith('http'):
                                resource = {
                                    'name': name,
                                    'url': url,
                                    'speed': 5.0,  #  5MB/s
                                    'is_whitelist': True,
                                    'category': ''
                                }
                                whitelist_resources.append(resource)
        
            print(f"  : {len(whitelist_resources)} ")
        except Exception as e:
            print(f"  : {e}")
        
        return whitelist_resources
    
    def _read_step6_csv_resources(self, file_path: str) -> List[Dict[str, Any]]:
        """ Step6 CSV """
        resources = []
        lines = []
        
        #  UTF-8
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            print(f"  UTF-8 Step6 CSV")
        except UnicodeDecodeError:
            print("  UTF-8 Step6 CSV")
            return resources
        except Exception as e:
            print(f"  Step6 CSV: {e}")
            return resources
        
        current_category = ""
        current_speed = 0.0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 
            if line.startswith('#') and ('Step6' in line or '' in line or '' in line or line.startswith('#' * 50)):
                continue
            
            #  # [ 0.582MB/s
            if line.startswith('# [') and 'MB/s' in line:
                try:
                    # 
                    if ']' in line:
                        category_part = line[line.find('[') + 1:line.find(']')]
                        if category_part:
                            current_category = category_part.strip()
                    
                    # 
                    if 'MB/s' in line:
                        speed_part = line[line.find('MB/s') - 10:line.find('MB/s')]
                        speed_str = speed_part.strip().split()[-1]
                        try:
                            current_speed = float(speed_str)
                        except ValueError:
                            current_speed = 0.0
                except Exception:
                    pass
                continue
            
            # 
            if line.startswith('#') or not line:
                continue
            
            # 
            if ',' in line:
                parts = line.split(',')
                if len(parts) >= 2:
                    name = parts[0].strip()
                    url = parts[1].strip()
                    
                    # Parse speed from the third column if available
                    speed = current_speed
                    if len(parts) >= 3:
                        try:
                            speed = float(parts[2].strip())
                        except ValueError:
                            speed = current_speed
                    
                    if name and url and url.startswith('http'):
                        resource = {
                            'name': name,
                            'url': url,
                            'speed': speed,
                            'category': current_category
                        }
                        resources.append(resource)
        
        return resources
    
    def _generate_results(self, video_resources: List[dict]):
        """  -  name_filtering_rules.txt order step6_video_resources.csv"""
        from pathlib import Path
        from datetime import datetime
        import re
        
        #  output 
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        #  whitelist 
        whitelist_resources = self._load_whitelist_resources()
        
        #  1:  name_filtering_rules.txt 
        template_file = Path("name_filtering_rules.txt")
        if not template_file.exists():
            print(f"Template file not found: {template_file}")
            return
        
        with open(template_file, 'r', encoding='utf-8') as f:
            template_lines = f.readlines()
        
        # Parse template
        template_structure = self._parse_template(template_lines)
        
        #  2:  
        step6_le_resources = []
        step6_lu_resources = []
        step6_used_resources = set()  # Track used step6 resources to avoid duplication
        
        # Collect step6 resources by category according to template order
        category_step6_resources = {}  # Store resources by category name
        
        print(f"  {len(video_resources)} ")
        
        for resource in video_resources[:10]:  # Debug: only check first 10 resources
            resource_id = (resource['name'], resource['url'])
            resource_name_lower = resource['name'].lower()
            speed = resource.get('speed', 0)
            
            print(f"  : {resource['name']} (speed: {speed})")
            
            if resource_id not in step6_used_resources:
                # Find which category this resource belongs to by checking all keywords
                for item in template_structure:
                    if item['type'] == 'category':
                        keywords = item['keywords']
                        category_name = item['name']
                        
                        # Check if resource matches any keyword in this category
                        matched = False
                        for keyword in keywords:
                            if keyword.lower() in resource_name_lower:
                                print(f"    : {category_name} - : {keyword}")
                                # Add resource to this category
                                if category_name not in category_step6_resources:
                                    category_step6_resources[category_name] = []
                                
                                category_step6_resources[category_name].append(resource)
                                step6_used_resources.add(resource_id)
                                matched = True
                                break  # Stop checking other keywords for this resource
                        
                        if matched:
                            break  # Stop checking other categories once matched
                else:
                    print(f"    : ")
        
        print(f"  : {len(category_step6_resources)} ")
        for cat_name, resources in category_step6_resources.items():
            print(f"  {cat_name}: {len(resources)} ")
        
        # Now collect resources by speed requirements, maintaining category order
        for item in template_structure:
            if item['type'] == 'category':
                category_name = item['name']
                
                if category_name in category_step6_resources:
                    # Process resources in this category
                    for resource in category_step6_resources[category_name]:
                        speed = resource.get('speed', 0)
                        
                        # Add to appropriate speed category
                        if speed >= 1.0:
                            step6_le_resources.append(resource)
                        if speed >= 0.2:
                            step6_lu_resources.append(resource)
                            print(f"  LU: {resource['name']} (speed: {speed})")  # Debug output
        
        # Now, process remaining resources (those not selected by step6 rules) with whitelist
        remaining_step6_resources = []
        for resource in video_resources:
            resource_id = (resource['name'], resource['url'])
            if resource_id not in step6_used_resources:
                remaining_step6_resources.append(resource)
        
        # Combine remaining step6 resources with whitelist for additional processing
        additional_resources = remaining_step6_resources + whitelist_resources
        
        # Classify additional resources by speed
        additional_le_resources = []
        additional_lu_resources = []
        
        for resource in additional_resources:
            speed = resource.get('speed', 0)
            if speed >= 1.0:
                additional_le_resources.append(resource)
            if speed >= 0.2:
                additional_lu_resources.append(resource)
        
        # Generate files with step6 resources first (strict template order), then additional resources
        le_file = output_dir / "LE.txt"
        lu_file = output_dir / "LU.txt"
        
        # Generate files with step6 resources first (strict template order), then additional resources
        le_file = output_dir / "LE.txt"
        lu_file = output_dir / "LU.txt"
        
        # Generate complete files with both step6 and additional resources
        step6_le_count, additional_le_count = self._generate_file_by_template_combined(le_file, step6_le_resources, additional_le_resources, template_structure, "LE")
        step6_lu_count, additional_lu_count = self._generate_file_by_template_combined(lu_file, step6_lu_resources, additional_lu_resources, template_structure, "LU")
        
        # Total counts
        total_le_count = step6_le_count + additional_le_count
        total_lu_count = step6_lu_count + additional_lu_count
        
        # Statistics
        total_channels = len(set(r['name'] for r in video_resources))
        step6_le_unique = len(set(r['name'] for r in step6_le_resources))
        step6_lu_unique = len(set(r['name'] for r in step6_lu_resources))
        total_le_unique = len(set(r['name'] for r in step6_le_resources + additional_le_resources))
        total_lu_unique = len(set(r['name'] for r in step6_lu_resources + additional_lu_resources))
        
        print(f"Generated LE.txt: {total_le_count} resources (>= 1.0 MB/s)")
        print(f"  - Step6 resources (template order): {step6_le_count}")
        print(f"  - Additional resources: {additional_le_count}")
        print(f"Generated LU.txt: {total_lu_count} resources (>= 0.2 MB/s)")
        print(f"  - Step6 resources (template order): {step6_lu_count}")
        print(f"  - Additional resources: {additional_lu_count}")
        print(f"Total channels: {total_channels}")
        print(f"Step6 qualified: LE={step6_le_unique}, LU={step6_lu_unique}")
        print(f"Total qualified: LE={total_le_unique}, LU={total_lu_unique}")
        print(f"Files generated: LE.txt + LU.txt (Step6 resources in strict template order + additional resources)")
    
    def _parse_template(self, template_lines):
        """ """
        structure = []
        current_category = None
        current_keywords = []
        
        for line in template_lines:
            line = line.strip()
            
            if not line:  # 
                structure.append({'type': 'empty', 'content': ''})
                continue
            
            if '#genre#' in line:
                # 
                if current_category:
                    structure.append({
                        'type': 'category',
                        'name': current_category,
                        'keywords': current_keywords
                    })
                
                # 
                current_category = line.split('#genre#')[0].strip()
                current_keywords = []
                structure.append({'type': 'header', 'content': line})
            elif current_category and line:
                # 
                current_keywords.append(line)
        
        # 
        if current_category:
            structure.append({
                'type': 'category',
                'name': current_category,
                'keywords': current_keywords
            })
        
        return structure
    
    def _generate_file_by_template_step6(self, output_file, resources, template_structure, file_type, is_step6_part):
        """Generate files according to template - for step6 resources (strict order) or additional resources"""
        mode = 'a' if not is_step6_part else 'w'  # Append for additional, write for step6
        
        with open(output_file, mode, encoding='utf-8') as f:
            total_count = 0
            
            for item in template_structure:
                if item['type'] == 'empty':
                    f.write('\n')
                elif item['type'] == 'header':
                    f.write(item['content'] + '\n')
                elif item['type'] == 'category':
                    # For step6 resources: write resources already classified by category
                    if is_step6_part:
                        # Resources are already pre-classified by category during processing
                        # We need to extract resources that belong to this category
                        category_name = item['name']
                        category_resources = []
                        
                        # Find resources that match this category's keywords
                        for resource in resources:
                            for keyword in item['keywords']:
                                if keyword.lower() in resource['name'].lower():
                                    category_resources.append(resource)
                                    break  # Stop checking other keywords for this resource
                        
                        # Sort and write resources for this category
                        sorted_resources = self._sort_resources(category_resources)
                        for resource in sorted_resources:
                            f.write(f"{resource['name']},{resource['url']}\n")
                            total_count += 1
                    else:
                        # For additional resources: use keyword matching
                        category_resources = self._classify_resources_by_keywords(
                            resources, item['keywords']
                        )
                        sorted_resources = self._sort_resources(category_resources)
                        
                        for resource in sorted_resources:
                            f.write(f"{resource['name']},{resource['url']}\n")
                            total_count += 1
            
            return total_count
    
    def _generate_file_by_template_combined(self, output_file, step6_resources, additional_resources, template_structure, file_type):
        """Generate files with combined step6 and additional resources without duplicate headers"""
        with open(output_file, 'w', encoding='utf-8') as f:
            total_count = 0
            step6_count = 0
            additional_count = 0
            
            # Track used resources to avoid duplication across categories
            used_step6_resources = set()
            used_additional_resources = set()
            
            for item in template_structure:
                if item['type'] == 'empty':
                    f.write('\n')
                elif item['type'] == 'header':
                    f.write(item['content'] + '\n')
                elif item['type'] == 'category':
                    category_name = item['name']
                    
                    # Collect step6 resources for this category (only unused ones)
                    step6_category_resources = []
                    for resource in step6_resources:
                        resource_id = (resource['name'], resource['url'])
                        if resource_id not in used_step6_resources:
                            for keyword in item['keywords']:
                                # Improved matching: remove spaces and special characters for comparison
                                clean_keyword = keyword.replace(' ', '').replace('!', '').lower()
                                clean_resource_name = resource['name'].replace(' ', '').replace('!', '').lower()
                                if clean_keyword in clean_resource_name or keyword.lower() in resource['name'].lower():
                                    step6_category_resources.append(resource)
                                    used_step6_resources.add(resource_id)
                                    break
                    
                    # Collect additional resources for this category (only unused ones)
                    additional_category_resources = []
                    for resource in additional_resources:
                        resource_id = (resource['name'], resource['url'])
                        if resource_id not in used_additional_resources:
                            for keyword in item['keywords']:
                                # Improved matching: remove spaces and special characters for comparison
                                clean_keyword = keyword.replace(' ', '').replace('!', '').lower()
                                clean_resource_name = resource['name'].replace(' ', '').replace('!', '').lower()
                                if clean_keyword in clean_resource_name or keyword.lower() in resource['name'].lower():
                                    additional_category_resources.append(resource)
                                    used_additional_resources.add(resource_id)
                                    break
                    
                    # Sort and write all resources for this category
                    all_category_resources = step6_category_resources + additional_category_resources
                    # Sort resources by keyword order in template, then by name
                    sorted_resources = self._sort_resources_by_keyword_order(all_category_resources, item['keywords'])
                    
                    for resource in sorted_resources:
                        f.write(f"{resource['name']},{resource['url']}\n")
                        total_count += 1
                        
                        # Count separately for statistics
                        if resource in step6_resources:
                            step6_count += 1
                        else:
                            additional_count += 1
            
            return step6_count, additional_count
    
    def _classify_resources_by_keywords(self, resources, keywords):
        """ """
        classified_resources = []
        used_resources = set()  # 
        
        for keyword in keywords:
            for resource in resources:
                resource_id = (resource['name'], resource['url'])  # 
                
                if resource_id not in used_resources:
                    # 
                    resource_name = resource['name']
                    
                    if keyword.lower() in resource_name.lower():
                        # 
                        classified_resources.append(resource)
                        used_resources.add(resource_id)
        
        return classified_resources
    
    def _sort_resources_by_keyword_order(self, resources, keywords):
        """Sort resources by keyword order in template, then by custom rules"""
        if not resources:
            return []
        
        # Create keyword order mapping
        keyword_order = {keyword.lower(): idx for idx, keyword in enumerate(keywords)}
        
        def get_keyword_order(resource):
            """Find the keyword order for this resource"""
            resource_name_lower = resource['name'].lower()
            for keyword in keywords:
                clean_keyword = keyword.replace(' ', '').replace('!', '').lower()
                clean_resource_name = resource['name'].replace(' ', '').replace('!', '').lower()
                if clean_keyword in clean_resource_name or keyword.lower() in resource_name_lower:
                    return keyword_order[keyword.lower()]
            return float('inf')  # If no keyword match, put at end
        
        def extract_cctv_number(name):
            """Extract CCTV number for sorting"""
            import re
            match = re.search(r'^(CCTV[-\s]*)(\d+)', name, re.IGNORECASE)
            if match:
                return int(match.group(2))
            return float('inf')  # Non-CCTV channels
        
        def extract_speed_from_url(url):
            """Extract speed value from URL"""
            import re
            # Look for .speed=number pattern in URL
            match = re.search(r'\.speed=(\d+(?:\.\d+)?)', url)
            if match:
                return float(match.group(1))
            return 0  # Default speed if not found
        
        def sort_key(resource):
            """Custom sort key function"""
            name = resource['name']
            url = resource['url']
            
            # Primary sort: keyword order
            keyword_order_val = get_keyword_order(resource)
            
            # Secondary sort: CCTV number (ascending for CCTV channels)
            cctv_number = extract_cctv_number(name)
            
            # Tertiary sort: speed value (descending for same names)
            speed_val = extract_speed_from_url(url)
            
            # For same names, we want higher speed first (negative for descending)
            # For different names, speed doesn't matter as much
            return (keyword_order_val, cctv_number, -speed_val, name)
        
        return sorted(resources, key=sort_key)
    
    def _sort_resources(self, resources):
        """ sorting resources - implement user's specific sorting requirements"""
        if not resources:
            return []
        
        def extract_cctv_number(name):
            """Extract CCTV number for sorting (ascending)"""
            import re
            match = re.search(r'^(CCTV[-\s]*)(\d+)', name, re.IGNORECASE)
            if match:
                return int(match.group(2))
            return float('inf')  # Non-CCTV channels go to the end
        
        def extract_speed_from_url(url):
            """Extract speed value from URL"""
            import re
            # Look for .speed=number pattern in URL
            match = re.search(r'\.speed=(\d+(?:\.\d+)?)', url)
            if match:
                return float(match.group(1))
            return 0  # Default speed if not found
        
        def sort_key(resource):
            """Custom sort key function"""
            name = resource['name']
            url = resource['url']
            
            # Primary sort: CCTV number (ascending for CCTV channels)
            cctv_number = extract_cctv_number(name)
            
            # Secondary sort: speed value (descending for same names)
            speed_val = extract_speed_from_url(url)
            
            # Tertiary sort: name (for final tie-breaker)
            return (cctv_number, -speed_val, name)
        
        return sorted(resources, key=sort_key)
    
    def _run_conversion_tools(self):
        """  -  exe output"""
        import subprocess
        import shutil
        from pathlib import Path
        
        # 
        output_dir = Path("output")
        utils_dir = Path("utils")
        
        #  Python 
        py_source = Path("utils/txt_to_m3u8b.py")  # Python 
        
        #  Python 
        if not py_source.exists():
            print(f" Python : {py_source}")
            return
        
        #  LE.txt  LU.txt 
        le_file = output_dir / "LE.txt"
        lu_file = output_dir / "LU.txt"
        
                
        if le_file.exists():
            print(f" LE.txt -> LE.m3u")
            try:
                #  Python 
                try:
                    le_txt_path = output_dir / "LE.txt"
                    le_m3u_path = output_dir / "LE.m3u"
                    result = subprocess.run(["python", str(py_source), str(le_txt_path), str(le_m3u_path)], 
                                         check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
                    print(f" LE.m3u (Python)")
                except (subprocess.CalledProcessError, FileNotFoundError) as e:
                    print(f" Python: {str(e)}")
                    
            except Exception as e:
                print(f" : {e}")
        
        if lu_file.exists():
            print(f" LU.txt -> LU.m3u")
            try:
                #  Python 
                try:
                    lu_txt_path = output_dir / "LU.txt"
                    lu_m3u_path = output_dir / "LU.m3u"
                    result = subprocess.run(["python", str(py_source), str(lu_txt_path), str(lu_m3u_path)], 
                                         check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
                    print(f" LU.m3u (Python)")
                except (subprocess.CalledProcessError, FileNotFoundError) as e:
                    print(f" Python: {str(e)}")
            except Exception as e:
                print(f" : {e}")
    
    def _verify_generated_files(self):
        """ """
        import datetime
        
        output_dir = Path("output")
        files_to_check = ["LE.txt", "LU.txt", "LE.m3u", "LU.m3u"]
        
        print(f"\n  ")
        print("-" * 50)
        
        for filename in files_to_check:
            file_path = output_dir / filename
            if file_path.exists():
                # 
                file_size = file_path.stat().st_size
                mod_time = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
                
                print(f" {filename}: {file_size} bytes, : {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 
                if file_size == 0:
                    print(f" : {filename} ")
                else:
                    # 
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            first_line = f.readline().strip()
                            if first_line:
                                print(f"   : {first_line[:50]}...")
                    except Exception as e:
                        print(f"   : {e}")
            else:
                print(f" {filename}: ")
        
        print(f"\n : ")
        print(f" ")
    
    def run_full_process(self):
        """ """
        print("=" * 80)
        print(" Step7 ")
        print("=" * 80)
        
        main_start_time = time.time()
        
        try:
            # Step6
            step6_csv_path = "output/step6_video_resources.csv"
            
            if not Path(step6_csv_path).exists():
                print(f"Step6: {step6_csv_path}")
                return
            
            # Step6
            if not self._validate_step6_file(step6_csv_path):
                print("Step6")
                return
            
            video_resources = self._read_step6_csv_resources(step6_csv_path)
            
            if not video_resources:
                print("Step6")
                return
            
            print(f" {len(video_resources)} Step6")
            
            # Step7: 
            print(f"\n Step7: ")
            print("-" * 50)
            
            self._generate_results(video_resources)
            
            # Step8: 
            print(f"\n Step8: ")
            print("-" * 50)
            
            self._run_conversion_tools()
            
            # 
            main_end_time = time.time()
            print(f"\n !: {self._format_duration(main_end_time - main_start_time)}")
            print(f" Step7: Step6={len(video_resources)}")
            
            # 
            self._verify_generated_files()
            
        except Exception as e:
            print(f" Step7: {e}")
            import traceback
            traceback.print_exc()
    
    def _validate_step6_file(self, file_path: str) -> bool:
        """ Step6 """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                if not first_line:
                    print(f"Step6: ")
                    return False
                
                # 
                if 'Step6' in first_line or '' in first_line or '#' in first_line:
                    print(f"Step6")
                    return True
                else:
                    print(f"Step6, ")
                    return True
                        
        except UnicodeDecodeError:
            print(f"Step6, ")
            return False
                
        except Exception as e:
            print(f"Step6: {e}")
            return False
    
    def _format_duration(self, seconds: float) -> str:
        """ """
        if seconds < 60:
            return f"{seconds:.1f}"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            remaining_seconds = seconds % 60
            return f"{minutes}{remaining_seconds:.1f}"
        else:
            hours = int(seconds // 3600)
            remaining_minutes = int((seconds % 3600) // 60)
            remaining_seconds = seconds % 60
            return f"{hours}{remaining_minutes}{remaining_seconds:.1f}"

if __name__ == "__main__":
    #  - 
    checker = ThirdChecker1()
    checker.run_full_process()
