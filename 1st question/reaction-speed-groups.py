import pandas as pd
import numpy as np
import os
from demoparser2 import DemoParser
from awpy.visibility import VisibilityChecker
from awpy.data import TRIS_DIR
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

BASE_PATH = r"F:\steam\steamapps\common\Counter-Strike Global Offensive\game\csgo\replays"

DEMOS_AND_PLAYERS = [
    ("match730_003784446263911514537_1478082598_187.dem", 76561198262157518, "arckay."),
    ("match730_003784108645122310500_1981615639_411.dem", 76561198155980865, "KosyaK"),
    ("match730_003783868685299483229_2047292477_192.dem", 76561198962223770, "patsan"),
    ("match730_003788960304604381265_2009075138_192.dem", 76561198155980865, "KosyaK"),
    ("match730_003788558291370508879_1730936726_187.dem", 76561198155980865, "KosyaK"),
    ("match730_003790222312024835007_0827502415_272.dem", 76561198816184658, "Unknown"),
    ("match730_003790275752155414789_0281693499_411.dem", 76561198816184658, "Unknown"),
    ("match730_003790277747167723523_2066055668_187.dem", 76561198816184658, "Unknown"),
    ("match730_003790301240638832694_0587072542_186.dem", 76561198816184658, "Unknown"),
]

CSV_OUTPUT = "reaction_speed_comparison.csv"
TICK_RATE = 64
LOOKBACK_WINDOW_SECONDS = 3.0
MAX_REACTION_TICKS = 200

TRACKED_STEAMIDS = set([float(76561198262157518), float(76561198155980865), float(76561198962223770), float(76561198816184658)])

print_lock = Lock()

def safe_print(msg):
    with print_lock:
        print(msg)

def process_demo(demo_file, tracked_steamid, player_name):
    demo_path = os.path.join(BASE_PATH, demo_file)
    
    if not os.path.exists(demo_path):
        safe_print(f"Warning: {demo_file} not found, skipping...")
        return None, None
    
    safe_print(f"\n{'='*60}")
    safe_print(f"Processing {demo_file}...")
    safe_print(f"{'='*60}")
    
    try:
        parser = DemoParser(demo_path)
        
        tick_df = parser.parse_ticks(["X", "Y", "Z", "is_alive", "name"])
        tick_df = pd.DataFrame(tick_df)
        tick_df = tick_df[tick_df['is_alive'] == True].sort_values(by=['steamid', 'tick'])
        
        kills_df = pd.DataFrame(parser.parse_event("player_death"))
        
        safe_print(f"  Parsing weapon fires...")
        fires_df = pd.DataFrame(parser.parse_event("weapon_fire"))
        
        header = parser.parse_header()
        map_name = header.get("map_name")
        
        tri_path = TRIS_DIR / f"{map_name}.tri"
        
        if not tri_path.exists():
            safe_print(f"  Warning: .tri file for {map_name} not found, skipping...")
            return None, None
        
        safe_print(f"  Initializing raycasting for {map_name}...")
        vc = VisibilityChecker(path=tri_path)
        
        safe_print(f"  Processing {len(kills_df)} kills...")
        
        tick_df['steamid'] = tick_df['steamid'].astype(float)
        ticks_indexed = tick_df.set_index(['tick', 'steamid']).sort_index()
        
        fires_df['user_steamid'] = fires_df['user_steamid'].astype(float)
        fires_indexed = fires_df.set_index(['tick', 'user_steamid']).sort_index()
        
        tracked_reactions = []
        other_reactions = []
        
        for _, kill in kills_df.iterrows():
            attacker_id = float(kill.get('attacker_steamid', 0))
            victim_id = float(kill.get('user_steamid', 0))
            kill_tick = int(kill.get('tick', 0))
            
            if not attacker_id or not victim_id or attacker_id == victim_id:
                continue
            
            start_search_tick = kill_tick - int(LOOKBACK_WINDOW_SECONDS * TICK_RATE)
            
            try:
                window_slice = ticks_indexed.loc[start_search_tick:kill_tick]
                att_hist = window_slice.xs(attacker_id, level='steamid')
                vic_hist = window_slice.xs(victim_id, level='steamid')
            except KeyError:
                continue
            
            merged = pd.merge(att_hist, vic_hist, on='tick', suffixes=('_att', '_vic'), how='inner').sort_index(ascending=False)
            
            spotted_tick = kill_tick
            
            for tick, row in merged.iterrows():
                p1 = (row['X_att'], row['Y_att'], row['Z_att'] + 64)
                p2 = (row['X_vic'], row['Y_vic'], row['Z_vic'] + 64)
                
                is_visible = vc.is_visible(p1, p2)
                
                if not is_visible:
                    spotted_tick = tick + 1
                    break
                
                spotted_tick = tick
            
            try:
                attacker_fires = fires_indexed.xs(attacker_id, level='user_steamid')
                first_shot_after_visible = attacker_fires[
                    (attacker_fires.index >= spotted_tick) & 
                    (attacker_fires.index <= kill_tick)
                ]
                
                if first_shot_after_visible.empty:
                    continue
                    
                first_shot_tick = first_shot_after_visible.index.min()
                
            except KeyError:
                continue
            
            reaction_ticks = first_shot_tick - spotted_tick
            
            if reaction_ticks > MAX_REACTION_TICKS or reaction_ticks < 0:
                continue
            
            reaction_time_ms = (reaction_ticks / TICK_RATE) * 1000
            
            reaction_data = {
                'reaction_time_ms': reaction_time_ms,
                'reaction_ticks': reaction_ticks
            }
            
            if attacker_id in TRACKED_STEAMIDS:
                tracked_reactions.append(reaction_data)
            else:
                other_reactions.append(reaction_data)
        
        safe_print(f"  Tracked reactions: {len(tracked_reactions)} | Other reactions: {len(other_reactions)}")
        
        return tracked_reactions, other_reactions
        
    except Exception as e:
        safe_print(f"  Error processing {demo_file}: {e}")
        return None, None

def main():
    all_tracked_reactions = []
    all_other_reactions = []
    
    safe_print(f"Processing {len(DEMOS_AND_PLAYERS)} demos using multithreading...\n")
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_demo = {
            executor.submit(process_demo, demo_file, steamid, name): demo_file 
            for demo_file, steamid, name in DEMOS_AND_PLAYERS
        }
        
        for future in as_completed(future_to_demo):
            tracked_reactions, other_reactions = future.result()
            
            if tracked_reactions:
                all_tracked_reactions.extend(tracked_reactions)
            if other_reactions:
                all_other_reactions.extend(other_reactions)
    
    if not all_tracked_reactions and not all_other_reactions:
        safe_print("\nNo reaction data collected!")
        return
    
    safe_print(f"\n{'='*60}")
    safe_print("AGGREGATING RESULTS...")
    safe_print(f"{'='*60}")
    
    comparison_data = []
    
    if all_tracked_reactions:
        tracked_df = pd.DataFrame(all_tracked_reactions)
        comparison_data.append({
            'group': 'Tracked Players',
            'total_reactions_analyzed': len(tracked_df),
            'avg_reaction_time_ms': tracked_df['reaction_time_ms'].mean(),
            'median_reaction_time_ms': tracked_df['reaction_time_ms'].median(),
            'min_reaction_time_ms': tracked_df['reaction_time_ms'].min(),
            'max_reaction_time_ms': tracked_df['reaction_time_ms'].max(),
            'std_reaction_time_ms': tracked_df['reaction_time_ms'].std(),
            'avg_reaction_ticks': tracked_df['reaction_ticks'].mean()
        })
    
    if all_other_reactions:
        other_df = pd.DataFrame(all_other_reactions)
        comparison_data.append({
            'group': 'Other Players',
            'total_reactions_analyzed': len(other_df),
            'avg_reaction_time_ms': other_df['reaction_time_ms'].mean(),
            'median_reaction_time_ms': other_df['reaction_time_ms'].median(),
            'min_reaction_time_ms': other_df['reaction_time_ms'].min(),
            'max_reaction_time_ms': other_df['reaction_time_ms'].max(),
            'std_reaction_time_ms': other_df['reaction_time_ms'].std(),
            'avg_reaction_ticks': other_df['reaction_ticks'].mean()
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    comparison_df = comparison_df.round(2)
    
    comparison_df.to_csv(CSV_OUTPUT, index=False)
    
    safe_print(f"\nReaction speed comparison saved to {CSV_OUTPUT}")
    safe_print(f"\n{'='*60}")
    safe_print("REACTION SPEED COMPARISON")
    safe_print(f"{'='*60}\n")
    safe_print(comparison_df.to_string(index=False))
    
    if len(comparison_df) == 2:
        diff_avg = comparison_df.iloc[0]['avg_reaction_time_ms'] - comparison_df.iloc[1]['avg_reaction_time_ms']
        diff_median = comparison_df.iloc[0]['median_reaction_time_ms'] - comparison_df.iloc[1]['median_reaction_time_ms']
        
        safe_print(f"\n{'='*60}")
        safe_print("DIFFERENCE (Tracked - Other):")
        safe_print(f"{'='*60}")
        safe_print(f"Average reaction speed difference: {diff_avg:.2f} ms")
        safe_print(f"Median reaction speed difference: {diff_median:.2f} ms")

if __name__ == "__main__":
    main()