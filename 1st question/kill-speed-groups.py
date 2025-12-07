import pandas as pd
import numpy as np
import os
from demoparser2 import DemoParser
from awpy.visibility import VisibilityChecker
from awpy.data import TRIS_DIR

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

CSV_OUTPUT = "kill_speed_comparison.csv"
TICK_RATE = 64
LOOKBACK_WINDOW_SECONDS = 3.0
MAX_KILL_SPEED_TICKS = 150

TRACKED_STEAMIDS = set([float(76561198262157518), float(76561198155980865), float(76561198962223770), float(76561198816184658)])

def main():
    all_tracked_kills = []
    all_other_kills = []
    
    for demo_file, tracked_steamid, player_name in DEMOS_AND_PLAYERS:
        demo_path = os.path.join(BASE_PATH, demo_file)
        
        if not os.path.exists(demo_path):
            print(f"Warning: {demo_file} not found, skipping...")
            continue
        
        print(f"\n{'='*60}")
        print(f"Processing {demo_file}...")
        print(f"{'='*60}")
        
        try:
            parser = DemoParser(demo_path)
            
            tick_df = parser.parse_ticks(["X", "Y", "Z", "is_alive", "name"])
            tick_df = pd.DataFrame(tick_df)
            tick_df = tick_df[tick_df['is_alive'] == True].sort_values(by=['steamid', 'tick'])
            
            kills_df = pd.DataFrame(parser.parse_event("player_death"))
            
            header = parser.parse_header()
            map_name = header.get("map_name")
            
            tri_path = TRIS_DIR / f"{map_name}.tri"
            
            if not tri_path.exists():
                print(f"  Warning: .tri file for {map_name} not found, skipping...")
                continue
            
            print(f"  Initializing raycasting for {map_name}...")
            vc = VisibilityChecker(path=tri_path)
            
            print(f"  Processing {len(kills_df)} kills...")
            
            tick_df['steamid'] = tick_df['steamid'].astype(float)
            ticks_indexed = tick_df.set_index(['tick', 'steamid']).sort_index()
            
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
                
                kill_speed_ticks = kill_tick - spotted_tick
                
                if kill_speed_ticks > MAX_KILL_SPEED_TICKS:
                    continue
                
                kill_speed_ms = (kill_speed_ticks / TICK_RATE) * 1000
                
                kill_data = {
                    'kill_speed_ms': kill_speed_ms,
                    'kill_speed_ticks': kill_speed_ticks
                }
                
                if attacker_id in TRACKED_STEAMIDS:
                    all_tracked_kills.append(kill_data)
                else:
                    all_other_kills.append(kill_data)
            
            print(f"  Tracked players kills: {len([k for k in all_tracked_kills if k])} | Other players kills: {len([k for k in all_other_kills if k])}")
            
        except Exception as e:
            print(f"  Error processing {demo_file}: {e}")
            continue
    
    if not all_tracked_kills and not all_other_kills:
        print("\nNo kill data collected!")
        return
    
    print(f"\n{'='*60}")
    print("AGGREGATING RESULTS...")
    print(f"{'='*60}")
    
    comparison_data = []
    
    if all_tracked_kills:
        tracked_df = pd.DataFrame(all_tracked_kills)
        comparison_data.append({
            'group': 'Tracked Players',
            'total_kills_analyzed': len(tracked_df),
            'avg_kill_speed_ms': tracked_df['kill_speed_ms'].mean(),
            'median_kill_speed_ms': tracked_df['kill_speed_ms'].median(),
            'min_kill_speed_ms': tracked_df['kill_speed_ms'].min(),
            'max_kill_speed_ms': tracked_df['kill_speed_ms'].max(),
            'std_kill_speed_ms': tracked_df['kill_speed_ms'].std(),
            'avg_kill_speed_ticks': tracked_df['kill_speed_ticks'].mean()
        })
    
    if all_other_kills:
        other_df = pd.DataFrame(all_other_kills)
        comparison_data.append({
            'group': 'Other Players',
            'total_kills_analyzed': len(other_df),
            'avg_kill_speed_ms': other_df['kill_speed_ms'].mean(),
            'median_kill_speed_ms': other_df['kill_speed_ms'].median(),
            'min_kill_speed_ms': other_df['kill_speed_ms'].min(),
            'max_kill_speed_ms': other_df['kill_speed_ms'].max(),
            'std_kill_speed_ms': other_df['kill_speed_ms'].std(),
            'avg_kill_speed_ticks': other_df['kill_speed_ticks'].mean()
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    comparison_df = comparison_df.round(2)
    
    comparison_df.to_csv(CSV_OUTPUT, index=False)
    
    print(f"\nKill speed comparison saved to {CSV_OUTPUT}")
    print(f"\n{'='*60}")
    print("KILL SPEED COMPARISON")
    print(f"{'='*60}\n")
    print(comparison_df.to_string(index=False))
    
    if len(comparison_df) == 2:
        diff_avg = comparison_df.iloc[0]['avg_kill_speed_ms'] - comparison_df.iloc[1]['avg_kill_speed_ms']
        diff_median = comparison_df.iloc[0]['median_kill_speed_ms'] - comparison_df.iloc[1]['median_kill_speed_ms']
        
        print(f"\n{'='*60}")
        print("DIFFERENCE (Tracked - Other):")
        print(f"{'='*60}")
        print(f"Average kill speed difference: {diff_avg:.2f} ms")
        print(f"Median kill speed difference: {diff_median:.2f} ms")

if __name__ == "__main__":
    main()