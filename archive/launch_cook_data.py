import cook_data

if __name__ == "__main__":
    # Since the .so file is primarily a library, ensure its GUI logic or callable main function is invoked here.
    cook_data.root.mainloop()  # Assuming the GUI's `root` object is exposed in the .so file
