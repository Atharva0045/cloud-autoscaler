def update_loop(interval=300):  # 5 minutes
    while True:
        df = fetch_live_window()
        df.to_csv("data/live_buffer.csv", index=False)
        print("✅ live_buffer.csv updated (5-minute window)")
        time.sleep(interval)

