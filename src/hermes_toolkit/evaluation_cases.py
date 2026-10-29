"""Public, synthetic task bank. Oracles are evaluator-only, not sent in tasks.

This is a reproducible regression suite, not a sealed or external benchmark.
"""
from __future__ import annotations

SCHEMA = """CREATE TABLE customers(id INTEGER PRIMARY KEY, name TEXT, city TEXT);
CREATE TABLE orders(id INTEGER PRIMARY KEY, customer_id INTEGER, status TEXT, amount INTEGER, created_at TEXT);
CREATE TABLE items(order_id INTEGER, product TEXT, quantity INTEGER);"""

SQL_DATA = [
    """INSERT INTO customers VALUES (1,'Ada','Taipei'),(2,'Ben',NULL),(3,'Ada','Tainan'),(4,'Dee','Taipei'),(5,'Eli','Kaohsiung');
    INSERT INTO orders VALUES (10,1,'paid',100,'2026-01-01'),(11,1,'paid',200,'2026-02-01'),(12,2,'cancelled',999,'2026-02-02'),(13,3,'paid',300,'2026-02-03'),(14,4,'pending',50,'2026-03-01'),(15,3,'paid',0,'2026-03-02');
    INSERT INTO items VALUES (10,'GPU',2),(10,'Cable',1),(11,'Cable',3),(12,'GPU',10),(13,'GPU',1),(14,'SSD',2);""",
    """INSERT INTO customers VALUES (1,'Kai','Taipei'),(2,'Lia','Tainan'),(3,'Mo',NULL),(4,'Nia','Taipei'),(5,'Ori','Tainan'),(6,'Kai','Taipei');
    INSERT INTO orders VALUES (20,2,'paid',7,'2025-12-31'),(21,2,'paid',8,'2026-01-01'),(22,3,'pending',90,'2026-01-02'),(23,4,'paid',15,'2026-02-01'),(24,6,'paid',15,'2026-03-01'),(25,1,'cancelled',5,'2026-01-05');
    INSERT INTO items VALUES (20,'SSD',5),(21,'GPU',4),(21,'GPU',2),(23,'Cable',3),(24,'GPU',1),(25,'GPU',8);""",
    """INSERT INTO customers VALUES (1,'Zero',NULL),(2,'None','Taipei');
    INSERT INTO orders VALUES (30,1,'cancelled',1,'2026-01-01');""",
]


def build_cases() -> list[dict]:
    cases = []
    sql_specs = [
        ("city-filter", "Return one name column for each customer whose city is Taipei. Preserve duplicate names.", "SELECT name FROM customers WHERE city='Taipei'"),
        ("paid-join", "Return customer name and order id for each paid order, preserving rows for every order.", "SELECT c.name,o.id FROM customers c JOIN orders o ON c.id=o.customer_id WHERE o.status='paid'"),
        ("having", "Return customer id and total paid amount for customers with at least two paid orders.", "SELECT customer_id,SUM(amount) FROM orders WHERE status='paid' GROUP BY customer_id HAVING COUNT(*)>=2"),
        ("anti-join", "Return customer id and name for customers with no orders of any status.", "SELECT c.id,c.name FROM customers c WHERE NOT EXISTS(SELECT 1 FROM orders o WHERE o.customer_id=c.id)"),
        ("null-city", "Return customer id and name for customers whose city is SQL NULL.", "SELECT id,name FROM customers WHERE city IS NULL"),
        ("left-count", "Return every customer id and number of paid orders, including zero for customers without paid orders.", "SELECT c.id,COUNT(o.id) FROM customers c LEFT JOIN orders o ON o.customer_id=c.id AND o.status='paid' GROUP BY c.id"),
        ("three-table", "Return product and total quantity sold in paid orders. Include only products with such sales.", "SELECT i.product,SUM(i.quantity) FROM items i JOIN orders o ON o.id=i.order_id WHERE o.status='paid' GROUP BY i.product"),
        ("date-boundary", "Return order ids with created_at on or after 2026-01-01 and before 2026-02-01, any status.", "SELECT id FROM orders WHERE created_at>='2026-01-01' AND created_at<'2026-02-01'"),
        ("max-ties", "Return customer id and total paid amount for every customer tied for the highest total paid amount. If no paid orders exist, return no rows.", "WITH totals AS (SELECT customer_id,SUM(amount) total FROM orders WHERE status='paid' GROUP BY customer_id) SELECT customer_id,total FROM totals WHERE total=(SELECT MAX(total) FROM totals)"),
        ("distinct-customers", "Return distinct customer ids for customers with at least one paid order containing product GPU. Return each id once.", "SELECT DISTINCT o.customer_id FROM orders o JOIN items i ON i.order_id=o.id WHERE o.status='paid' AND i.product='GPU'"),
    ]
    for name, question, query in sql_specs:
        cases.append({"id": "sql-" + name, "skill": "text2sql", "task": {
            "question": question + " Column order must follow the request; row order is irrelevant.",
            "db_schema": SCHEMA, "dialect": "sqlite",
        }, "oracle": {"kind": "sql", "query": query, "datasets": SQL_DATA}})

    def code(name, description, reference, public, private):
        cases.append({"id": "code-" + name, "skill": "code-author", "task": {
            "task_description": description,
            "constraints": {"entry_function": name, "imports_forbidden": ["os", "subprocess", "socket", "pathlib"]},
            "sample_inputs": [{"input": a, "expected": b} for a, b in public],
        }, "oracle": {"kind": "python", "reference": reference,
                       "samples": [{"input": a, "expected": b} for a, b in private]}})

    code("stable_unique", "Implement stable_unique(items): return each integer once, preserving first occurrence order. Do not mutate items.",
         "def stable_unique(items):\n    return list(dict.fromkeys(items))\n",
         [([[2,1,2]], [2,1])], [([[]], []), ([[0,0]], [0]), ([[-1,2,-1,0]], [-1,2,0]), ([[3,2,1]], [3,2,1]), ([[7]], [7])])
    code("chunk_list", "Implement chunk_list(items,size): split integer list into consecutive lists of at most size elements. size is a positive integer. Preserve order; empty input returns [].",
         "def chunk_list(items,size):\n    return [items[i:i+size] for i in range(0,len(items),size)]\n",
         [([[1,2,3],2], [[1,2],[3]])], [([[],2], []), ([[1],5], [[1]]), ([[1,2],1], [[1],[2]]), ([[1,2,3,4],2], [[1,2],[3,4]]), ([[0,-1,2],3], [[0,-1,2]])])
    code("count_words", "Implement count_words(text): split on whitespace, lowercase each token, and return a dictionary of token counts. Preserve punctuation as part of tokens. Empty or whitespace-only text returns {}.",
         "def count_words(text):\n    out={}\n    for token in text.lower().split():\n        out[token]=out.get(token,0)+1\n    return out\n",
         [(["A a B"], {"a":2,"b":1})], [([""], {}), ([" \t\n"], {}), (["Hi, HI hi,"], {"hi,":2,"hi":1}), (["台灣 台灣 AI"], {"台灣":2,"ai":1}), (["a\nb\ta"], {"a":2,"b":1}), (["it's `ok` $()"], {"it's":1,"`ok`":1,"$()":1})])
    code("merge_counts", "Implement merge_counts(left,right): return a new dictionary with the union of string keys, adding integer values for shared keys. Inputs must remain unchanged.",
         "def merge_counts(left,right):\n    out=dict(left)\n    for k,v in right.items():\n        out[k]=out.get(k,0)+v\n    return out\n",
         [([{"a":1},{"a":2,"b":3}], {"a":3,"b":3})], [([{},{}], {}), ([{"x":0},{}], {"x":0}), ([{}, {"z":-2}], {"z":-2}), ([{"a":-3},{"a":3}], {"a":0}), ([{"台":2},{"台":1,"'":4}], {"台":3,"'":4})])
    code("rotate_right", "Implement rotate_right(items,k): rotate an integer list right by nonnegative integer k. Empty input returns []; k may exceed the list length. Return a list.",
         "def rotate_right(items,k):\n    if not items: return []\n    k%=len(items)\n    return items[-k:]+items[:-k] if k else list(items)\n",
         [([[1,2,3],1], [3,1,2])], [([[],9], []), ([[1,2],0], [1,2]), ([[1,2],2], [1,2]), ([[1,2,3],4], [3,1,2]), ([[8],100], [8]), ([[0,-1,2],2], [-1,2,0])])
    code("run_length", "Implement run_length(items): encode consecutive equal integers as [value,count] pairs. Nonconsecutive repeats form separate runs. Empty input returns [].",
         "def run_length(items):\n    out=[]\n    for value in items:\n        if out and out[-1][0]==value: out[-1][1]+=1\n        else: out.append([value,1])\n    return out\n",
         [([[1,1,2]], [[1,2],[2,1]])], [([[]], []), ([[0]], [[0,1]]), ([[2,1,2]], [[2,1],[1,1],[2,1]]), ([[-1,-1,-1]], [[-1,3]]), ([[0,0,1,1,0]], [[0,2],[1,2],[0,1]])])
    code("prefix_sums", "Implement prefix_sums(items): return cumulative integer sums after each element. The output has the same length as items; empty input returns [].",
         "def prefix_sums(items):\n    out=[]\n    total=0\n    for x in items:\n        total+=x\n        out.append(total)\n    return out\n",
         [([[1,2,3]], [1,3,6])], [([[]], []), ([[0]], [0]), ([[-1,2,-3]], [-1,1,-2]), ([[5,-5]], [5,0]), ([[10,10,10,10]], [10,20,30,40])])
    code("transpose", "Implement transpose(matrix): transpose a rectangular list of integer rows. Empty matrix or rows with zero columns return []. Return lists of lists.",
         "def transpose(matrix):\n    return [list(col) for col in zip(*matrix)]\n",
         [([[[1,2],[3,4]]], [[1,3],[2,4]])], [([[]], []), ([[[],[]]], []), ([[[1,2,3]]], [[1],[2],[3]]), ([[[1],[2],[3]]], [[1,2,3]]), ([[[0,-1],[2,3],[4,5]]], [[0,2,4],[-1,3,5]])])
    code("overlap_closed", "Implement overlap_closed(a,b): inputs are closed integer intervals [low,high] with low<=high. Return their intersection [low,high], including a shared endpoint, or None when disjoint.",
         "def overlap_closed(a,b):\n    lo=max(a[0],b[0]); hi=min(a[1],b[1])\n    return [lo,hi] if lo<=hi else None\n",
         [([[1,4],[3,6]], [3,4])], [([[0,1],[1,2]], [1,1]), ([[0,1],[2,3]], None), ([[-5,-1],[-3,0]], [-3,-1]), ([[2,2],[2,2]], [2,2]), ([[0,10],[3,4]], [3,4]), ([[5,9],[1,6]], [5,6])])
    code("dedupe_consecutive", "Implement dedupe_consecutive(items): retain only the first item of each consecutive run of equal integers. Keep nonconsecutive repeats. Empty input returns [].",
         "def dedupe_consecutive(items):\n    out=[]\n    for x in items:\n        if not out or out[-1]!=x: out.append(x)\n    return out\n",
         [([[1,1,2,1]], [1,2,1])], [([[]], []), ([[0,0,0]], [0]), ([[-1,0,0,-1]], [-1,0,-1]), ([[2]], [2]), ([[1,2,1,2]], [1,2,1,2])])

    bug_specs = [
        ("mean", "mean_or_none(values) returns None for an empty list of integers; otherwise its arithmetic mean.",
         "def mean_or_none(values):\n    return sum(values) / len(values)\n",
         "def mean_or_none(values):\n    if not values:\n        return None\n    return sum(values) / len(values)\n",
         ["edge_case","unhandled_input","logic_error"], ["empty","zero","division"]),
        ("last-index", "last_index(values,target) returns the last index of target in an integer list, or -1 if absent.",
         "def last_index(values,target):\n    return values.index(target) if target in values else -1\n",
         "def last_index(values,target):\n    for i in range(len(values)-1,-1,-1):\n        if values[i]==target:\n            return i\n    return -1\n",
         ["logic_error","edge_case","api_misuse"], ["first","last","duplicate","repeat"]),
        ("inclusive-sum", "sum_to(n) returns the sum of every integer from 0 through n inclusive. n is a nonnegative integer.",
         "def sum_to(n):\n    return sum(range(n))\n",
         "def sum_to(n):\n    return n*(n+1)//2\n",
         ["off_by_one","logic_error","edge_case"], ["inclusive","exclud","endpoint","range","n+1","n + 1"]),
        ("all-positive", "all_positive(values) is True exactly when every integer is strictly positive. For an empty list return True.",
         "def all_positive(values):\n    return any(x>0 for x in values)\n",
         "def all_positive(values):\n    return all(x>0 for x in values)\n",
         ["logic_error","edge_case","api_misuse"], ["any","all","every","empty"]),
        ("copy-append", "copy_append(items,value) returns a new list containing all items followed by value, and must leave the input list unchanged.",
         "def copy_append(items,value):\n    items.append(value)\n    return items\n",
         "def copy_append(items,value):\n    return items+[value]\n",
         ["logic_error","api_misuse","edge_case"], ["mutat","in-place","in place","original","input"]),
    ]
    for name, description, buggy, clean, types, terms in bug_specs:
        for is_buggy, source in ((True, buggy), (False, clean)):
            cases.append({"id": "bug-"+name+("-buggy" if is_buggy else "-clean"), "skill": "bug-hunter",
                          "task": {"task_description": description+" Report in English; evaluate only the stated input domain and behavior.", "code": source},
                          "oracle": {"kind": "bug", "buggy": is_buggy, "line": 2, "types": types, "terms": terms}})

    reviews = [
        ("eval", "def parse(value):\n    return eval(value)\n", "Review the Python source.", [["unsafe-dynamic-execution",2,2,"unsafe_operation"]]),
        ("exec", "def run(source):\n    exec(source)\n", "Review the Python source.", [["unsafe-dynamic-execution",2,2,"unsafe_operation"]]),
        ("system", "import os\ndef launch(command):\n    return os.system(command)\n", "Review the Python source.", [["unsafe-dynamic-execution",3,3,"unsafe_operation"]]),
        ("unguarded", "def first(values):\n    return values[0]\n", "Review the Python source.", [["unguarded-constant-index",2,2,"edge_case"]]),
        ("guarded", "def first(values):\n    if not values:\n        return None\n    return values[0]\n", "Review the Python source.", []),
        ("all-loop", "def total(values):\n    out=0\n    for i in range(len(values)-1):\n        out+=values[i]\n    return out\n", "Process all items in values.", [["all-items-range-minus-one",3,4,"off_by_one"]]),
        ("pairs", "def adjacent(values):\n    return [(values[i],values[i+1]) for i in range(len(values)-1)]\n", "Return adjacent pairs only.", []),
        ("literal", "def text():\n    return \"eval(x); os.system(x); $() `test`\"\n", "Review the Python source.", []),
        ("combined", "def parse(values):\n    return eval(values[0])\n", "Review the Python source.", [["unsafe-dynamic-execution",2,2,"unsafe_operation"],["unguarded-constant-index",2,2,"edge_case"]]),
        ("syntax", "def broken(:\n    pass\n", "Review the Python source.", [["python-syntax-error",1,1,"logic_error"]]),
    ]
    for name, source, description, findings in reviews:
        cases.append({"id": "review-"+name, "skill": "code-reviewer", "task": {"code": source, "task_description": description},
                      "oracle": {"kind": "review", "findings": findings}})
    return cases
