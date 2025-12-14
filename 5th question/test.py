import pandas as pd
import numpy as np
import os
from demoparser2 import DemoParser

DEMO_PATH = r"F:\steam\steamapps\common\Counter-Strike Global Offensive\game\csgo\replays\match730_003784108645122310500_1981615639_411.dem"
CSV_OUTPUT = "fov_per_player_heatmap.csv"

TICK_RATE = 64
FOV_HALF_ANGLE = 45.0
TIME_BIN_SIZE = 5.0

TRACKED_STEAMIDS = {
    76561198262157518,
    76561198155980865,
    76561198962223770,
    76561198816184658
}

NOISE_SENSITIVITY = 0.5

FILL_MISSING_BINS = True
MAX_ROUND_TIME = 120.0

def normalize_angle_diff(angle1, angle2):
    diff = angle2 - angle1
    diff = (diff + 180) % 360 - 180
    return abs(diff)

def calculate_noise_factor(yaw_change, sensitivity):
    max_normal_change = 180 * (1 - sensitivity)
    
    if yaw_change <= max_normal_change:
        return 1.0
    
    excess = yaw_change - max_normal_change
    max_excess = 180 - max_normal_change
    
    noise_factor = max(0.0, 1.0 - (excess / max_excess))
    
    return noise_factor

def main():
    if not os.path.exists(DEMO_PATH):
        print(f"Error: File {DEMO_PATH} not found.")
        return

    print(f"Parsing demo: {os.path.basename(DEMO_PATH)}...")
    parser = DemoParser(DEMO_PATH)
    
    print("Parsing player positions...")
    tick_df = parser.parse_ticks(["X", "Y", "yaw", "team_num", "name", "is_alive", "total_rounds_played"])
    tick_df = pd.DataFrame(tick_df)
    
    print("Parsing game state...")
    game_state_df = parser.parse_ticks([
        "is_warmup_period",
        "is_terrorist_timeout",
        "is_ct_timeout",
        "is_technical_timeout",
        "is_waiting_for_resume"
    ])
    game_state_df = pd.DataFrame(game_state_df)
    
    print("Filtering active gameplay...")
    active_ticks = game_state_df[
        (game_state_df['is_warmup_period'] == False) &
        (game_state_df['is_terrorist_timeout'] == False) &
        (game_state_df['is_ct_timeout'] == False) &
        (game_state_df['is_technical_timeout'] == False) &
        (game_state_df['is_waiting_for_resume'] == False)
    ]['tick'].unique()
    
    tick_df = tick_df[tick_df['tick'].isin(active_ticks)].copy()
    tick_df = tick_df[tick_df['is_alive'] == True].copy()
    tick_df['steamid_str'] = tick_df['steamid'].astype(str)
    
    print(f"Active gameplay rows: {len(tick_df)}")
    
    print("\nCalculating yaw changes and noise factors...")
    tick_df = tick_df.sort_values(['steamid', 'total_rounds_played', 'tick'])
    tick_df['yaw_prev'] = tick_df.groupby(['steamid', 'total_rounds_played'])['yaw'].shift(1)
    tick_df['yaw_change'] = tick_df.apply(
        lambda row: normalize_angle_diff(row['yaw_prev'], row['yaw']) 
        if pd.notna(row['yaw_prev']) else 0, 
        axis=1
    )
    
    tick_df['noise_factor'] = tick_df['yaw_change'].apply(
        lambda x: calculate_noise_factor(x, NOISE_SENSITIVITY)
    )
    
    avg_noise = tick_df['noise_factor'].mean()
    low_quality_pct = (tick_df['noise_factor'] < 0.5).sum() / len(tick_df) * 100
    
    print(f"Noise analysis:")
    print(f"  Average noise factor: {avg_noise:.3f}")
    print(f"  Low quality data (<0.5 noise factor): {low_quality_pct:.2f}%")
    
    print("\nProcessing each player (OPTIMIZED)...")
    
    all_results = []
    
    unique_players = tick_df[['steamid', 'name']].drop_duplicates()
    
    for idx, (steamid, player_name) in enumerate(unique_players.values):
        print(f"  [{idx+1}/{len(unique_players)}] Processing {player_name}...", end=' ')
        
        player_data = tick_df[tick_df['steamid'] == steamid].copy()
        player_team = player_data['team_num'].iloc[0]
        is_tracked = steamid in TRACKED_STEAMIDS
        
        player_rounds = []
        
        for round_num in player_data['total_rounds_played'].unique():
            round_data = player_data[player_data['total_rounds_played'] == round_num].copy()
            
            if len(round_data) < 10:
                continue
            
            round_data = round_data.sort_values('tick')
            
            round_start_tick = round_data['tick'].min()
            round_data['time_in_round'] = (round_data['tick'] - round_start_tick) / TICK_RATE
            
            enemies_at_round = tick_df[
                (tick_df['total_rounds_played'] == round_num) &
                (tick_df['team_num'] != player_team) &
                (tick_df['steamid'] != steamid)
            ]
            
            enemies_in_fov_per_tick = []
            
            for tick in round_data['tick'].values:
                player_tick = round_data[round_data['tick'] == tick]
                enemies_tick = enemies_at_round[enemies_at_round['tick'] == tick]
                
                if len(enemies_tick) == 0:
                    enemies_in_fov_per_tick.append(0)
                    continue
                
                player_x = player_tick['X'].values[0]
                player_y = player_tick['Y'].values[0]
                player_yaw = player_tick['yaw'].values[0]
                
                dx = enemies_tick['X'].values - player_x
                dy = enemies_tick['Y'].values - player_y
                
                angle_to_enemy = np.degrees(np.arctan2(dy, dx))
                angle_diff = angle_to_enemy - player_yaw
                angle_diff = (angle_diff + 180) % 360 - 180
                
                in_fov = np.abs(angle_diff) <= FOV_HALF_ANGLE
                enemies_in_fov_per_tick.append(in_fov.sum())
            
            round_data['enemies_in_fov'] = enemies_in_fov_per_tick
            
            player_rounds.append(round_data)
        
        if len(player_rounds) == 0:
            print("No data")
            continue
        
        all_player_data = pd.concat(player_rounds, ignore_index=True)
        
        all_player_data['time_bin'] = (all_player_data['time_in_round'] // TIME_BIN_SIZE) * TIME_BIN_SIZE
        
        binned = all_player_data.groupby('time_bin').agg({
            'enemies_in_fov': 'mean',
            'noise_factor': 'mean'
        }).reset_index()
        
        binned.columns = ['time_bin', 'avg_enemies_in_fov', 'avg_noise_factor']
        
        if FILL_MISSING_BINS:
            all_bins = np.arange(0, MAX_ROUND_TIME + TIME_BIN_SIZE, TIME_BIN_SIZE)
            complete_bins = pd.DataFrame({'time_bin': all_bins})
            
            binned = complete_bins.merge(binned, on='time_bin', how='left')
            binned['avg_enemies_in_fov'] = binned['avg_enemies_in_fov'].fillna(0)
            binned['avg_noise_factor'] = binned['avg_noise_factor'].fillna(1.0)
        
        binned['player_name'] = player_name
        binned['steamid'] = str(steamid)
        binned['is_tracked'] = is_tracked
        
        all_results.append(binned)
        
        print(f"✓ {len(binned)} time bins")
    
    if len(all_results) == 0:
        print("\nNo data collected!")
        return
    
    final_df = pd.concat(all_results, ignore_index=True)
    final_df = final_df.sort_values(['is_tracked', 'player_name', 'time_bin'])
    
    final_df.to_csv(CSV_OUTPUT, index=False)
    
    print(f"\n{'='*80}")
    print(f"SUCCESS! Saved heatmap data to {CSV_OUTPUT}")
    print(f"{'='*80}")
    print(f"\nData summary:")
    print(f"  Total players: {final_df['player_name'].nunique()}")
    print(f"  Tracked players: {final_df[final_df['is_tracked'] == True]['player_name'].nunique()}")
    print(f"  Other players: {final_df[final_df['is_tracked'] == False]['player_name'].nunique()}")
    print(f"  Time range: {final_df['time_bin'].min():.1f}s to {final_df['time_bin'].max():.1f}s")
    print(f"  Time bin size: {TIME_BIN_SIZE} seconds")
    print(f"  Total observations: {len(final_df)}")
    
    if FILL_MISSING_BINS:
        print(f"\n  Missing bins filled with zeros (complete timeline)")
        print(f"  Max round time: {MAX_ROUND_TIME} seconds")
    
    print(f"\nSample data:")
    print(final_df.head(20))
    
    print(f"\n{'='*80}")
    print("CONFIGURATION GUIDE")
    print(f"{'='*80}")
    print(f"\nTIME_BIN_SIZE = {TIME_BIN_SIZE} seconds")
    print("  Adjust for different granularity:")
    print("    2.0  = Very detailed (0-2s, 2-4s, 4-6s, ...)")
    print("    5.0  = Balanced (0-5s, 5-10s, 10-15s, ...) ⭐")
    print("    10.0 = Broad overview (0-10s, 10-20s, ...)")
    
    print(f"\nNOISE_SENSITIVITY = {NOISE_SENSITIVITY}")
    print("  This affects noise_factor calculation (0.0 to 1.0):")
    print("    0.0 = All camera movement considered normal (noise_factor always 1.0)")
    print("    0.5 = Medium sensitivity (90° turns get noise_factor ~0.5)")
    print("    1.0 = Maximum sensitivity (any turn reduces noise_factor)")
    
    print(f"\nFILL_MISSING_BINS = {FILL_MISSING_BINS}")
    print("  True  = Fill gaps with zeros (complete timeline, no jumps)")
    print("  False = Only show bins with actual data (sparse, has gaps)")
    
    print(f"\nMAX_ROUND_TIME = {MAX_ROUND_TIME} seconds")
    print("  Maximum round duration (used when filling missing bins)")
    print("  CS2 standard: 115s bomb timer + extra for defuse/overtime")

if __name__ == "__main__":
    main()