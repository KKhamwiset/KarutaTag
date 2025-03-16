try:
    import sys
    import pandas as pd
    import requests
    from bs4 import BeautifulSoup
    import io
    from PIL import Image, ImageTk
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    import threading
    import urllib.parse
    import os
    import time
    import re
except ImportError as e:
    print(f"Error: Missing dependency - {e}")
    print("\nPlease install required packages using:")
    print("pip install pandas requests beautifulsoup4 pillow")
    if "tkinter" in str(e):
        print("\nNote: Tkinter should be included with Python, but may need to be installed separately.")
        print("- On Windows: Reinstall Python and check 'tcl/tk and IDLE'")
        print("- On Linux: sudo apt-get install python3-tk")
        print("- On Mac: brew install python-tk")
    sys.exit(1)

class KarutaImageFinder:
    def __init__(self, root):
        self.root = root
        self.root.title("Karuta Card Image Finder")
        self.root.geometry("1000x700")
        self.root.configure(bg="#f0f0f0")
        
        # Data storage
        self.cards_df = None
        self.current_image = None
        self.search_results = {}  # Cache for search results
        
        # Sorting options
        self.sort_enabled = tk.BooleanVar(value=True)
        self.sort_ascending = tk.BooleanVar(value=False)  # Default: highest burn value first
        
        # Set up the UI
        try:
            self.setup_ui()
            self.setup_sort_controls()
        except Exception as e:
            messagebox.showerror("UI Error", f"Error setting up UI: {str(e)}")
            raise
    
    def setup_ui(self):
        # Top frame for file loading
        top_frame = tk.Frame(self.root, bg="#f0f0f0")
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(top_frame, text="CSV File:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.file_entry = tk.Entry(top_frame, width=50)
        self.file_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="Browse", command=self.browse_file).pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="Load", command=self.load_file).pack(side=tk.LEFT, padx=5)
        
        # Initialize tag tracking
        self.tag_cards = {
            "burn": set(),
            "cute": set(),
            "favorite": set(),
            "good": set(),
            "ok": set(),
            "wife": set()
        }
        
        # Main content frame
        content_frame = tk.Frame(self.root, bg="#f0f0f0")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - card list
        left_panel = tk.Frame(content_frame, bg="#f0f0f0", width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        left_panel.pack_propagate(False)
        
        # Search box
        search_frame = tk.Frame(left_panel, bg="#f0f0f0")
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(search_frame, text="Search:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.search_entry = tk.Entry(search_frame)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.search_entry.bind("<KeyRelease>", self.filter_cards)
        
        # Card list with scrollbar
        list_frame = tk.Frame(left_panel, bg="#f0f0f0")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.card_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=25, font=("Arial", 10))
        self.card_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.card_listbox.yview)
        
        self.card_listbox.bind("<<ListboxSelect>>", self.on_card_select)
        
        # Right panel - card details and image
        right_panel = tk.Frame(content_frame, bg="#f0f0f0")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Card details
        self.details_frame = tk.Frame(right_panel, bg="#f0f0f0")
        self.details_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Character and Series labels
        tk.Label(self.details_frame, text="Character:", bg="#f0f0f0", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.character_label = tk.Label(self.details_frame, text="", bg="#f0f0f0", font=("Arial", 12))
        self.character_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        tk.Label(self.details_frame, text="Series:", bg="#f0f0f0", font=("Arial", 12, "bold")).grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.series_label = tk.Label(self.details_frame, text="", bg="#f0f0f0", font=("Arial", 12))
        self.series_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Code and Quality labels
        tk.Label(self.details_frame, text="Code:", bg="#f0f0f0", font=("Arial", 12, "bold")).grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.code_label = tk.Label(self.details_frame, text="", bg="#f0f0f0", font=("Arial", 12))
        self.code_label.grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        
        # Make burn value more prominent with gold star
        tk.Label(self.details_frame, text="Burn Value:", bg="#f0f0f0", font=("Arial", 12, "bold")).grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        self.quality_label = tk.Label(self.details_frame, text="", bg="#f0f0f0", font=("Arial", 16, "bold"), fg="#FF9900")
        self.quality_label.grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)
        
        # Search buttons
        button_frame = tk.Frame(right_panel, bg="#f0f0f0")
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Button(button_frame, text="Search Image", command=self.search_image).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Save Image", command=self.save_image).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Next Result", command=self.next_result).pack(side=tk.LEFT, padx=5)
        
        # Tag buttons frame
        tag_frame = tk.Frame(right_panel, bg="#f0f0f0")
        tag_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(tag_frame, text="Tag Card:", bg="#f0f0f0", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        
        # Create buttons for each tag type with different colors
        tag_colors = {
            "burn": "#ff6b6b",     # Red
            "cute": "#feca57",     # Yellow
            "favorite": "#ff9ff3", # Pink
            "good": "#1dd1a1",     # Green
            "ok": "#54a0ff",       # Blue
            "wife": "#5f27cd"      # Purple
        }
        
        for tag in ["burn", "cute", "favorite", "good", "ok", "wife"]:
            button = tk.Button(
                tag_frame, 
                text=tag.title(), 
                bg=tag_colors[tag],
                fg="white",
                command=lambda t=tag: self.tag_current_card(t)
            )
            button.pack(side=tk.LEFT, padx=3)
        
        # Command generation frame
        cmd_frame = tk.Frame(right_panel, bg="#f0f0f0")
        cmd_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Text field to display command
        tk.Label(cmd_frame, text="Karuta Command:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.command_var = tk.StringVar()
        self.command_entry = tk.Entry(cmd_frame, width=40, textvariable=self.command_var, state="readonly")
        self.command_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Generate and copy buttons
        tk.Button(cmd_frame, text="Generate", command=self.generate_command).pack(side=tk.LEFT, padx=3)
        tk.Button(cmd_frame, text="Copy", command=self.copy_command).pack(side=tk.LEFT, padx=3)
        tk.Button(cmd_frame, text="Clear Tags", command=self.clear_tags).pack(side=tk.LEFT, padx=3)
        
        # Tag status frame
        tag_status_frame = tk.Frame(right_panel, bg="#f0f0f0")
        tag_status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(tag_status_frame, text="Tagged Cards:", bg="#f0f0f0", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.tag_status_var = tk.StringVar(value="None")
        tk.Label(tag_status_frame, textvariable=self.tag_status_var, bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        
        # Image display
        self.image_frame = tk.Frame(right_panel, bg="#f0f0f0", height=400, width=600)
        self.image_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.image_label = tk.Label(self.image_frame, bg="#e0e0e0", text="No image loaded")
        self.image_label.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_sort_controls(self):
        """Add sorting controls to the interface"""
        sort_frame = tk.Frame(self.root, bg="#f0f0f0")
        sort_frame.pack(fill=tk.X, padx=10, pady=5, before=self.details_frame)
        
        # Add sort checkbox
        sort_check = tk.Checkbutton(
            sort_frame, 
            text="Sort by Burn Value", 
            variable=self.sort_enabled,
            bg="#f0f0f0",
            command=self.apply_sort
        )
        sort_check.pack(side=tk.LEFT, padx=5)
        
        # Add ascending/descending radio buttons
        tk.Label(sort_frame, text="Sort Order:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        
        desc_radio = tk.Radiobutton(
            sort_frame,
            text="Highest First",
            variable=self.sort_ascending,
            value=False,
            bg="#f0f0f0",
            command=self.apply_sort
        )
        desc_radio.pack(side=tk.LEFT, padx=5)
        
        asc_radio = tk.Radiobutton(
            sort_frame,
            text="Lowest First",
            variable=self.sort_ascending,
            value=True,
            bg="#f0f0f0",
            command=self.apply_sort
        )
        asc_radio.pack(side=tk.LEFT, padx=5)
    
    def apply_sort(self):
        """Apply the current sort settings and refresh the list"""
        # Skip if no data loaded
        if self.cards_df is None:
            return
            
        # Refresh the list with current sort settings
        self.filter_cards()
    
    def browse_file(self):
        try:
            filename = filedialog.askopenfilename(
                title="Select CSV file",
                filetypes=(("CSV files", "*.csv"), ("All files", "*.*"))
            )
            if filename:
                self.file_entry.delete(0, tk.END)
                self.file_entry.insert(0, filename)
        except Exception as e:
            messagebox.showerror("Error", f"Error browsing for file: {str(e)}")
    
    def load_file(self):
        filepath = self.file_entry.get()
        if not filepath:
            messagebox.showerror("Error", "Please select a CSV file")
            return
        
        try:
            self.status_var.set("Loading CSV file...")
            self.root.update()
            
            # Check if file exists
            if not os.path.exists(filepath):
                messagebox.showerror("Error", f"File not found: {filepath}")
                self.status_var.set("Error: File not found")
                return
                
            # Load the CSV file
            try:
                self.cards_df = pd.read_csv(filepath)
                
                # Check if required columns exist
                required_cols = ['character', 'series', 'code', 'quality']
                missing_cols = [col for col in required_cols if col not in self.cards_df.columns]
                
                if missing_cols:
                    messagebox.showerror("Error", f"CSV is missing required columns: {', '.join(missing_cols)}")
                    self.status_var.set("Error: Invalid CSV format")
                    self.cards_df = None
                    return
                
                # Convert quality to numeric if it's not already
                if not pd.api.types.is_numeric_dtype(self.cards_df['quality']):
                    try:
                        self.cards_df['quality'] = pd.to_numeric(self.cards_df['quality'])
                    except:
                        messagebox.showwarning("Warning", "Could not convert quality values to numbers. Sorting may not work correctly.")
                
                # Sort cards by burn value (quality) if sorting is enabled
                if self.sort_enabled.get():
                    self.cards_df = self.cards_df.sort_values(
                        by='burnValue', 
                        ascending=self.sort_ascending.get()
                    ).reset_index(drop=True)
                
                # Clear the listbox
                self.card_listbox.delete(0, tk.END)
                
                # Populate the listbox with card names and burn value
                for idx, row in self.cards_df.iterrows():
                    char_name = row['character']
                    series_name = row['series']
                    bv = int(row['burnValue'])  # Convert to int to remove decimals
                    list_text = f"{bv} $ | {char_name} ({series_name})"
                    self.card_listbox.insert(tk.END, list_text)
                
                self.status_var.set(f"Loaded {len(self.cards_df)} cards from CSV")
            except pd.errors.EmptyDataError:
                messagebox.showerror("Error", "CSV file is empty")
                self.status_var.set("Error: Empty CSV file")
            except pd.errors.ParserError:
                messagebox.showerror("Error", "CSV parsing error. Check file format.")
                self.status_var.set("Error: CSV parsing error")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load CSV file: {str(e)}")
            self.status_var.set("Error loading CSV")
    
    def filter_cards(self, event=None):
        search_term = self.search_entry.get().lower()
        
        if not self.cards_df is None:
            # Clear the listbox
            self.card_listbox.delete(0, tk.END)
            
            # Apply sorting if enabled
            if self.sort_enabled.get():
                sorted_df = self.cards_df.sort_values(
                    by='burnValue', 
                    ascending=self.sort_ascending.get()
                )
            else:
                sorted_df = self.cards_df
            
            # Filter and repopulate
            for idx, row in sorted_df.iterrows():
                char_name = row['character']
                series_name = row['series']
                bv = int(row['burnValue'])  # Convert to int to remove decimals
                list_text = f"{bv} ★ | {char_name} ({series_name})"
                
                if search_term == "" or (search_term in char_name.lower() or search_term in series_name.lower()):
                    self.card_listbox.insert(tk.END, list_text)
            
            self.status_var.set(f"Found {self.card_listbox.size()} cards matching '{search_term}'")
    
    def on_card_select(self, event=None):
        # Get the selected index
        selection = self.card_listbox.curselection()
        if not selection:
            return
        
        # Get the name at the selected index
        selected_idx = selection[0]
        all_items = self.card_listbox.get(0, tk.END)
        selected_text = all_items[selected_idx]
        
        # Extract character and series from the text
        # Format is "Quality ★ | Character (Series)"
        parts = selected_text.split(" | ")
        if len(parts) < 2:
            return
            
        char_series = parts[1]  # This contains "Character (Series)"
        
        # Extract character and series
        char_end = char_series.rfind("(")
        if char_end > 0:
            char_name = char_series[:char_end].strip()
            series_name = char_series[char_end+1:].replace(")", "").strip()
            
            # Find the corresponding row in the dataframe
            for idx, row in self.cards_df.iterrows():
                if row['character'] == char_name and row['series'] == series_name:
                    # Update the labels
                    self.character_label.config(text=char_name)
                    self.series_label.config(text=series_name)
                    self.code_label.config(text=row['code'])
                    
                    # Make the quality more prominent with star symbol
                    bv = int(row['burnValue'])
                    self.quality_label.config(text=f"{bv} $")
                    
                    # Clear the image
                    self.current_image = None
                    self.image_label.config(image="", text="No image loaded")
                    
                    # Update tag status to highlight current card's tags
                    code = row['code']
                    current_tags = []
                    for tag, cards in self.tag_cards.items():
                        if code in cards:
                            current_tags.append(tag.title())
                    
                    if current_tags:
                        self.status_var.set(f"Card is tagged as: {', '.join(current_tags)}")
                    
                    break
    
    def search_image(self):
        char_name = self.character_label.cget("text")
        series_name = self.series_label.cget("text")
        
        if not char_name or not series_name:
            messagebox.showerror("Error", "Please select a card first")
            return
        
        # Clear any previous image
        self.image_label.config(image="", text="Searching for images...\nPlease wait...")
        
        # Start search in a separate thread
        search_thread = threading.Thread(target=self.simple_search_image, args=(char_name, series_name))
        search_thread.daemon = True
        search_thread.start()
    
    def simple_search_image(self, char_name, series_name):
        """A simple, reliable search method that uses standard web searches"""
        try:
            self.status_var.set(f"Searching for {char_name} from {series_name}...")
            self.root.update_idletasks()
            
            # Create a search key for caching
            search_key = f"{char_name}|{series_name}"
            
            # Check cache first
            if search_key in self.search_results and self.search_results[search_key]:
                image_urls = self.search_results[search_key]
                self.status_var.set(f"Found {len(image_urls)} cached images")
            else:
                # Build search queries
                queries = [
                    f"{char_name} {series_name}",  # Basic query
                    f"{char_name} {series_name} anime character",  # Specify anime character
                    f"{char_name} from {series_name}"  # Alternative format
                ]
                
                # Use the first query by default
                query = queries[0]
                
                # Headers to mimic a browser
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5'
                }
                
                # Simple approach to get images
                image_urls = []
                
                # Try Google Images first
                try:
                    encoded_query = urllib.parse.quote(query)
                    search_url = f"https://www.google.com/search?q={encoded_query}&tbm=isch"
                    
                    response = requests.get(search_url, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Extract all image elements
                        for img in soup.find_all('img'):
                            if img.has_attr('src') and ('http' in img['src'] or '//' in img['src']):
                                url = img['src']
                                if url.startswith('//'):
                                    url = 'https:' + url
                                if url not in image_urls and not url.endswith('.svg'):
                                    image_urls.append(url)
                        
                        # Look for image URLs in JSON data
                        scripts = soup.find_all("script")
                        for script in scripts:
                            script_text = script.string or ""
                            img_urls = re.findall(r'(https?://[^\s"\']+\.(jpg|jpeg|png|gif))', script_text)
                            for url, _ in img_urls:
                                if url not in image_urls:
                                    image_urls.append(url)
                                    
                        # Extract from possible JSON data
                        for script in soup.find_all('script'):
                            if script.string and '"ou":"http' in script.string:
                                matches = re.findall(r'"ou":"(http[^"]+)"', script.string)
                                for url in matches:
                                    if url not in image_urls:
                                        image_urls.append(url)
                except Exception as e:
                    print(f"Google search error: {str(e)}")
                
                # If Google didn't return enough, try Bing as backup
                if len(image_urls) < 5:
                    try:
                        encoded_query = urllib.parse.quote(query)
                        search_url = f"https://www.bing.com/images/search?q={encoded_query}&form=HDRSC2&first=1"
                        
                        response = requests.get(search_url, headers=headers, timeout=10)
                        
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.text, 'html.parser')
                            
                            # Extract from standard img tags
                            for img in soup.find_all('img'):
                                if img.has_attr('src') and ('http' in img['src'] or '//' in img['src']):
                                    url = img['src']
                                    if url.startswith('//'):
                                        url = 'https:' + url
                                    if url not in image_urls and not url.endswith('.svg'):
                                        image_urls.append(url)
                    except Exception as e:
                        print(f"Bing search error: {str(e)}")
                
                # Try a different query if we still don't have enough images
                if len(image_urls) < 5 and len(queries) > 1:
                    try:
                        encoded_query = urllib.parse.quote(queries[1])
                        search_url = f"https://www.google.com/search?q={encoded_query}&tbm=isch"
                        
                        response = requests.get(search_url, headers=headers, timeout=10)
                        
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.text, 'html.parser')
                            
                            # Extract all image elements
                            for img in soup.find_all('img'):
                                if img.has_attr('src') and ('http' in img['src'] or '//' in img['src']):
                                    url = img['src']
                                    if url.startswith('//'):
                                        url = 'https:' + url
                                    if url not in image_urls and not url.endswith('.svg'):
                                        image_urls.append(url)
                    except Exception as e:
                        print(f"Alternative query search error: {str(e)}")
                
                # Filter out small images, icons, etc.
                filtered_urls = []
                for url in image_urls:
                    # Skip likely non-image resources
                    if any(skip in url.lower() for skip in ['icon', 'logo', 'button', 'emoji', 'spinner', 'transparent']):
                        continue
                    # Skip SVGs
                    if url.lower().endswith('.svg'):
                        continue
                    # Skip very small URLs (likely thumbnails/icons)
                    if 'w=32' in url or 'w=16' in url or 'width=32' in url or 'width=16' in url:
                        continue
                    
                    filtered_urls.append(url)
                
                # Cache the results
                self.search_results[search_key] = filtered_urls
                self.status_var.set(f"Found {len(filtered_urls)} images")
                image_urls = filtered_urls
            
            # Display the first image
            if image_urls:
                self.current_result_index = 0
                self._display_image(image_urls[0])
            else:
                self.status_var.set("No images found")
                self.image_label.config(image="", text="No images found")
                
        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
            print(f"Error searching for image: {str(e)}")
    
    def _display_image(self, image_url):
        try:
            self.status_var.set(f"Loading image from {image_url[:50]}...")
            
            # Download the image with timeout and headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Referer': 'https://www.google.com/'
            }
            
            response = requests.get(image_url, headers=headers, timeout=10)
            
            # Check if we actually got an image
            content_type = response.headers.get('Content-Type', '')
            if not content_type.startswith('image/'):
                raise Exception(f"URL returned non-image content: {content_type}")
                
            image_data = response.content
            
            # Open and resize the image
            image = Image.open(io.BytesIO(image_data))
            
            # Ensure we have a standard RGB/RGBA image
            if image.mode not in ('RGB', 'RGBA'):
                image = image.convert('RGB')
            
            # Get frame size, with fallback for when frame isn't fully sized yet
            frame_width = max(self.image_frame.winfo_width(), 400) - 20
            frame_height = max(self.image_frame.winfo_height(), 300) - 20
            
            img_width, img_height = image.size
            
            # Skip if image is too small (likely an icon)
            if img_width < 100 or img_height < 100:
                raise Exception("Image too small, skipping to next")
                
            # Calculate resize ratio
            ratio = min(frame_width/img_width, frame_height/img_height)
            new_width = int(img_width * ratio)
            new_height = int(img_height * ratio)
            
            # Use LANCZOS for better quality or Nearest for speed
            # Handle different versions of PIL/Pillow
            try:
                if hasattr(Image, 'Resampling'):
                    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                else:
                    image = image.resize((new_width, new_height), Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.ANTIALIAS)
            except Exception:
                # Last resort fallback
                image = image.resize((new_width, new_height))
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(image)
            
            # Update the label
            self.image_label.config(image=photo, text="")
            self.image_label.image = photo  # Keep a reference
            self.current_image = image
            
            # Show image dimensions in status bar
            self.status_var.set(f"Image loaded: {img_width}x{img_height} pixels")
        except Exception as e:
            self.status_var.set(f"Error with image: {str(e)}")
            print(f"Image error ({image_url}): {str(e)}")
            
            # Try next image automatically if available
            search_key = f"{self.character_label.cget('text')}|{self.series_label.cget('text')}"
            if search_key in self.search_results and self.search_results[search_key]:
                image_urls = self.search_results[search_key]
                if hasattr(self, 'current_result_index') and len(image_urls) > 1:
                    self.current_result_index = (self.current_result_index + 1) % len(image_urls)
                    self._display_image(image_urls[self.current_result_index])
                else:
                    self.image_label.config(image="", text="Error loading image\nTry clicking 'Next Result'")
            else:
                self.image_label.config(image="", text="Error loading image\nTry searching again")
    
    def next_result(self):
        char_name = self.character_label.cget("text")
        series_name = self.series_label.cget("text")
        
        if not char_name or not series_name:
            return
        
        search_key = f"{char_name}|{series_name}"
        
        if search_key in self.search_results and self.search_results[search_key]:
            image_urls = self.search_results[search_key]
            
            if hasattr(self, 'current_result_index'):
                self.current_result_index = (self.current_result_index + 1) % len(image_urls)
                self._display_image(image_urls[self.current_result_index])
                self.status_var.set(f"Showing image {self.current_result_index + 1} of {len(image_urls)}")
            else:
                self.current_result_index = 0
                self._display_image(image_urls[0])
    
    def save_image(self):
        if not self.current_image:
            messagebox.showerror("Error", "No image to save")
            return
        
        char_name = self.character_label.cget("text")
        series_name = self.series_label.cget("text")
        code = self.code_label.cget("text")
        
        if not char_name or not series_name or not code:
            messagebox.showerror("Error", "Missing card information")
            return
        
        try:
            # Create a default filename
            default_name = f"{char_name}_{series_name}_{code}.png"
            default_name = default_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
            
            # Ask for save location
            file_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                initialfile=default_name,
                filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")]
            )
            
            if file_path:
                try:
                    # Save the image
                    self.current_image.save(file_path)
                    self.status_var.set(f"Image saved to {file_path}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save image: {str(e)}")
                    self.status_var.set("Error saving image")
        except Exception as e:
            messagebox.showerror("Error", f"Save dialog error: {str(e)}")
    
    def tag_current_card(self, tag):
        """Add the current card to the specified tag category"""
        code = self.code_label.cget("text")
        if not code:
            messagebox.showerror("Error", "No card selected")
            return
        
        # Add card to the tag set
        self.tag_cards[tag].add(code)
        
        # Update the tag status display
        self.update_tag_status()
        
        # Show confirmation
        self.status_var.set(f"Card {code} tagged as '{tag}'")
    
    def update_tag_status(self):
        """Update the tag status display"""
        status_text = []
        for tag, cards in self.tag_cards.items():
            if cards:
                status_text.append(f"{tag.title()}: {len(cards)}")
        
        if status_text:
            self.tag_status_var.set(", ".join(status_text))
        else:
            self.tag_status_var.set("None")
    
    def generate_command(self):
        """Generate Karuta commands for all tags"""
        tag_dropdown = tk.Toplevel(self.root)
        tag_dropdown.title("Generate Command")
        tag_dropdown.geometry("300x250")
        tag_dropdown.resizable(False, False)
        
        tk.Label(tag_dropdown, text="Select Tag:").pack(pady=10)
        
        # Create listbox for tags
        tag_listbox = tk.Listbox(tag_dropdown, height=6)
        tag_listbox.pack(fill=tk.X, padx=20, pady=5)
        
        # Add tags with card counts
        for tag in sorted(self.tag_cards.keys()):
            count = len(self.tag_cards[tag])
            tag_listbox.insert(tk.END, f"{tag.title()} ({count} cards)")
        
        def on_select():
            selection = tag_listbox.curselection()
            if not selection:
                messagebox.showinfo("Info", "Please select a tag")
                return
                
            # Get the selected tag
            selected_tag = list(sorted(self.tag_cards.keys()))[selection[0]]
            cards = self.tag_cards[selected_tag]
            
            if not cards:
                messagebox.showinfo("Info", f"No cards tagged as '{selected_tag}'")
                return
            
            # Generate command
            command = f"kt {selected_tag} {','.join(sorted(cards))}"
            self.command_var.set(command)
            
            # Close the window
            tag_dropdown.destroy()
            
            # Show confirmation
            self.status_var.set(f"Generated command for {len(cards)} cards tagged as '{selected_tag}'")
        
        tk.Button(tag_dropdown, text="Generate", command=on_select).pack(pady=10)
        tk.Button(tag_dropdown, text="Cancel", command=tag_dropdown.destroy).pack(pady=5)
        
        # Make window modal
        tag_dropdown.transient(self.root)
        tag_dropdown.grab_set()
        self.root.wait_window(tag_dropdown)
    
    def copy_command(self):
        """Copy the generated command to clipboard"""
        command = self.command_var.get()
        if not command:
            messagebox.showinfo("Info", "No command generated yet")
            return
        
        # Copy to clipboard
        self.root.clipboard_clear()
        self.root.clipboard_append(command)
        self.status_var.set("Command copied to clipboard")
    
    def clear_tags(self):
        """Clear all tagged cards"""
        if messagebox.askyesno("Confirm", "Clear all tagged cards?"):
            for tag in self.tag_cards:
                self.tag_cards[tag].clear()
            
            self.update_tag_status()
            self.command_var.set("")
            self.status_var.set("All tags cleared")


def main():
    try:
        root = tk.Tk()
        app = KarutaImageFinder(root)
        
        # Display usage instructions on startup
        messagebox.showinfo(
            "Karuta Image Finder - Instructions",
            "1. Click 'Browse' to locate your Karuta CSV file\n"
            "2. Click 'Load' to load your card collection\n"
            "3. Cards are sorted by burn value (highest first by default)\n"
            "4. Select a card from the list (use the search box to filter)\n" 
            "5. Click 'Search Image' to find images online\n"
            "6. Use 'Next Result' to browse through different images\n"
            "7. Use tag buttons to mark cards (Burn, Cute, etc.)\n"
            "8. Click 'Generate' to create Karuta commands\n"
            "9. Use 'Copy' to copy the command to clipboard\n\n"
            "Note: You can change sort order using the controls at the top."
        )
        
        root.mainloop()
    except Exception as e:
        print(f"Critical error starting application: {str(e)}")
        messagebox.showerror("Critical Error", f"Failed to start application: {str(e)}")

if __name__ == "__main__":
    main()