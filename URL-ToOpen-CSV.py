import scrape_regatta_results as scraper
import sys
import pandas as pd
import traceback

def main():
    print("Regatta Results Scraper")
    print("-" * 30)
    
    # Get URL from user if not provided as argument
    if len(sys.argv) > 1:
        url = sys.argv[1]
        print(f"Using provided URL: {url}")
    else:
        url = input("Please enter the regatta URL: ")
        if not url:
            url = "https://www.regattanetwork.com/clubmgmt/applet_regatta_results.php?regatta_id=29234&media_format=1"
            print(f"Using default URL: {url}")
    
    try:
        # Scrape results
        print("\nScraping results...")
        results_df = scraper.scrape_regatta_results(url)
        
        if results_df is not None and not results_df.empty:
            print("\nData successfully scraped!")
            print(f"Total entries found: {len(results_df)}")
            print("\nColumns found:", results_df.columns.tolist())
            
            # Clean the results
            print("\nCleaning data...")
            results_df = scraper.clean_results(results_df)
            
            # Display results for each category
            categories = results_df['Category'].unique()
            print(f"\nFound {len(categories)} categories:")
            
            for category in categories:
                print(f"\n{category} Results:")
                print("-" * 50)
                category_results = results_df[results_df['Category'] == category]
                print(f"Found {len(category_results)} entries")
                print(category_results.to_string(index=False))
            
            # Export in different formats
            print("\nExporting results...")
            scraper.export_results(results_df, 'csv')
            scraper.export_results(results_df, 'excel')
            scraper.export_results(results_df, 'json')
            
            print("\nResults have been saved as:")
            print("- output/regatta_results.csv")
            print("- output/regatta_results.xlsx")
            print("- output/regatta_results.json")
        else:
            print("\nNo results were found in the data")
        
    except Exception as e:
        print(f"\nError occurred: {str(e)}")
        print("\nFull error details:")
        traceback.print_exc()
    
    print("\nDone!")
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()
