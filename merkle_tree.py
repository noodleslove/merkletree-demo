import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Tuple

from pymerkle import InmemoryTree as MerkleTree
from pymerkle.hasher import MerkleHasher


def file_digest(file_path: Path):
    return hashlib.sha256(file_path.read_bytes()).digest()


def build_snapshot(root: Path) -> Tuple[MerkleTree, Dict[str, bytes]]:
    files = [p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]
    files.sort(key=lambda p: str(p.relative_to(root)))

    files_map: Dict[str, bytes] = {}
    tree = MerkleTree()

    for path in files:
        relative_path = str(path.relative_to(root))
        digest = file_digest(path)

        files_map[relative_path] = digest

        # incorporate both path and digest into the leaf hash
        leaf_payload = relative_path.encode() + b"::" + digest

        tree.append_entry(leaf_payload)

    return tree, files_map


def load_snapshot(path: Path) -> Tuple[str, Dict[str, bytes]]:
    if not path.exists():
        raise FileNotFoundError(f"Snapshot file {path} not found")
    with open(path, "r") as f:
        json_data = json.load(f)

    root = json_data.get("root", "")
    files_hex = json_data.get("files", {})
    files_map = {rel: bytes.fromhex(hh) for rel, hh in files_hex.items()}
    return root, files_map


def save_snapshot(path: Path, root: str, files_map: Dict[str, bytes]):
    json_data = {
        "root": root,
        "files": {rel: hh.hex() for rel, hh in files_map.items()},
    }
    with open(path, "w") as f:
        json.dump(json_data, f, indent=2)


def diff(
    old: Dict[str, bytes], new: Dict[str, bytes]
) -> Tuple[List[str], List[str], List[str]]:
    added = [p for p in new.keys() if p not in old.keys()]
    removed = [p for p in old.keys() if p not in new.keys()]
    modified = [p for p in old.keys() if p in new.keys() and old[p] != new[p]]
    return added, removed, modified


def demo():
    print("==  Snapshot 1")
    # list all files in the current dir, excluding the .git dir
    files = [f for f in Path(".").rglob("*") if f.is_file() and ".git" not in f.parts]
    print("==    Files:", [f.name for f in files])
    tree1, fm1 = build_snapshot(Path("."))
    print("==    Root hash:", tree1.get_state().hex())

    print("==  Snapshot 2")
    c_txt = Path("tests/c.txt")
    c_txt.parent.mkdir(parents=True, exist_ok=True)
    c_txt.write_text("hello")
    files2 = [f for f in Path(".").rglob("*") if f.is_file() and ".git" not in f.parts]
    print("==    Files:", [f.name for f in files2])
    tree2, fm2 = build_snapshot(Path("."))
    print("==    Root hash:", tree2.get_state().hex())

    if tree1.get_state() != tree2.get_state():
        print("==  Detected diff in root hash")
        hasher = MerkleHasher(tree2.algorithm, tree2.security)
        for idx, f in enumerate(sorted(files2), start=1):
            leaf_hash = tree2.get_leaf(idx)
            proof = tree2.prove_inclusion(idx)
            try:
                # verify if it exists in the previous state
                verify_ok = False
                # simplistic approach assumes same indexing
                # for real diff we need mapping of file -> index
                verify_ok = tree1.get_leaf(
                    idx
                ) == leaf_hash and tree1.get_state() == tree1.get_state(
                    tree1.get_size()
                )
            except Exception:
                verify_ok = False

            if not verify_ok:
                print(f"==    Diff found in {'/'.join(f.parts)}")
                print(f"==      Leaf hash: {leaf_hash.hex()}")
    else:
        print("==  No diff in root hash")

    c_txt.unlink()


def main():
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    RESET = "\033[0m"

    parser = argparse.ArgumentParser("MerkleTree based files diff demo")
    parser.add_argument("dir", type=str, help="Root directory to snapshot")
    parser.add_argument(
        "--snapshot",
        type=str,
        default="snapshot.json",
        help="Path for the snapshot file",
    )
    args = parser.parse_args()

    root = Path(args.dir).resolve()
    snapshot_path = Path(args.snapshot).resolve()

    print(f"== Building snapshot for path: {root}")
    tree1, files_map1 = build_snapshot(root)
    print(f"==    Root hash: {tree1.get_state().hex()}")

    tree0, files_map0 = None, None
    if snapshot_path.exists():
        print(f"==  Loading previous snapshot")
        tree0, files_map0 = load_snapshot(snapshot_path)
        print(f"==    Root hash: {tree0}")

    if tree0:
        print(f"==  Comparing snapshots")
        added, removed, modified = diff(files_map0, files_map1)

        if added or removed or modified:
            print(f"==  Detected diff in snapshots")
            if added:
                print(f"==    {GREEN}Added files: {added}{RESET}")
            if removed:
                print(f"==    {RED}Removed files: {removed}{RESET}")
            if modified:
                print(f"==    {YELLOW}Modified files: {modified}{RESET}")
        else:
            print(f"==  No diff in snapshots")
    else:
        print(f"==  No previous snapshot found")
    
    print(f"==  Saving current snapshot")
    save_snapshot(snapshot_path, tree1.get_state().hex(), files_map1)
    print(f"==  Saved snapshot to {snapshot_path}")


if __name__ == "__main__":
    main()
