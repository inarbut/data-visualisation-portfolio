import pandas as pd
import os
from awpy import Demo

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

CHEATER_STEAMIDS = {76561198262157518, 76561198155980865, 76561198962223770, 76561198816184658}

CSV_OUTPUT = "kills_with_cheater_flag.csv"

def main():
    all_kills = []
    
    for demo_file, tracked_steamid, player_name in DEMOS_AND_PLAYERS:
        demo_path = os.path.join(BASE_PATH, demo_file)
        
        if not os.path.exists(demo_path):
            print(f"Warning: {demo_file} not found, skipping...")
            continue
        
        print(f"\nProcessing {demo_file}...")
        
        try:
            dem = Demo(demo_path)
            dem.parse()
            
            kills_df = dem.kills.to_pandas()
            
            if len(kills_df) == 0:
                print(f"  No kills found in {demo_file}")
                continue
            
            kills_df['attacker_steamid'] = kills_df['attacker_steamid'].astype(str)
            kills_df['victim_steamid'] = kills_df['victim_steamid'].astype(str)
            
            kills_df['demo'] = demo_file
            
            cheater_steamids_str = {str(sid) for sid in CHEATER_STEAMIDS}
            kills_df['is_cheater'] = kills_df['attacker_steamid'].isin(cheater_steamids_str)
            
            selected_cols = ["attacker_steamid", "attacker_name", "victim_steamid", "victim_name", 
                           "headshot", "noscope", "thrusmoke", "penetrated", "is_cheater", "demo"]
            
            kills_subset = kills_df[selected_cols].copy()
            
            all_kills.append(kills_subset)
            
            cheater_kills = kills_subset['is_cheater'].sum()
            print(f"  Total kills: {len(kills_subset)}")
            print(f"  Cheater kills: {cheater_kills}")
            print(f"  Non-cheater kills: {len(kills_subset) - cheater_kills}")
            
        except Exception as e:
            print(f"  Error processing {demo_file}: {e}")
            continue
    
    if not all_kills:
        print("\nNo kill data collected!")
        return
    
    combined_df = pd.concat(all_kills, ignore_index=True)
    
    combined_df.to_csv(CSV_OUTPUT, index=False)
    
    print(f"\n{'='*80}")
    print(f"Kill statistics saved to {CSV_OUTPUT}")
    print(f"{'='*80}\n")
    
    print("Overall Summary:")
    print(f"  Total kills: {len(combined_df)}")
    print(f"  Cheater kills: {combined_df['is_cheater'].sum()}")
    print(f"  Non-cheater kills: {(~combined_df['is_cheater']).sum()}")
    print(f"\nKill statistics by cheater status:")
    print(combined_df.groupby('is_cheater')[['headshot', 'noscope', 'thrusmoke', 'penetrated']].mean().round(3))
    
    print(f"\nSample data:")
    print(combined_df.head(20))

if __name__ == "__main__":
    main()