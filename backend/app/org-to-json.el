(require 'org)
(require 'org-element)
(require 'json)

(defun cal-server/org-parse-timestamp (ts prefix)
  "Return an alist of structured timestamp info from org-element timestamp TS."
  (when ts
    (let* ((year-start (org-element-property :year-start ts))
	   (month-start (org-element-property :month-start ts))
	   (day-start (org-element-property :day-start ts))
	   (hour-start (org-element-property :hour-start ts))
	   (minute-start (org-element-property :minute-start ts))
	   (year-end (org-element-property :year-end ts))
	   (month-end (org-element-property :month-end ts))
	   (day-end (org-element-property :day-end ts))
	   (hour-end (org-element-property :hour-end ts))
	   (minute-end (org-element-property :minute-end ts))
	   (all-day (and (not hour-start) (not hour-end)))
	   (repeater (org-element-property :repeater-type ts))
	   (repeater-value (org-element-property :repeater-value ts))
	   (repeater-unit (org-element-property :repeater-unit ts))
	   (warning-type (org-element-property :warning-type ts))
	   (warning-value (org-element-property :warning-value ts))
	   (warning-unit (org-element-property :warning-unit ts)))
      (list
       (cons (intern (concat prefix "_start_date"))
	     (format "%04d-%02d-%02d" year-start month-start day-start))
       (cons (intern (concat prefix "_start_time"))
	     (when hour-start (format "%02d:%02d" hour-start (or minute-start 0))))
       (cons (intern (concat prefix "_end_date"))
	     (when year-end (format "%04d-%02d-%02d" year-end month-end day-end)))
       (cons (intern (concat prefix "_end_time"))
	     (when hour-end (format "%02d:%02d" hour-end (or minute-end 0))))
       (cons (intern (concat prefix "_all_day")) all-day)
       (cons (intern (concat prefix "_repeater_type")) repeater)
       (cons (intern (concat prefix "_repeater_value")) repeater-value)
       (cons (intern (concat prefix "_repeater_unit")) repeater-unit)
       (cons (intern (concat prefix "_warning_type")) warning-type)
       (cons (intern (concat prefix "_warning_value")) warning-value)
       (cons (intern (concat prefix "_warning_unit")) warning-unit)))))

(defun archive/org-extract-tasks ()
  "Extract tasks/events from current Org buffer and pring JSON."
  (let ((results '())
        (file (buffer-file-name)))
    (org-element-map (org-element-parse-buffer) 'headline
      (lambda (hl)
        (let* ((todo (org-element-property :todo-keyword hl))
               (title (org-element-property :raw-value hl))
               (scheduled (org-element-property :scheduled hl))
               (deadline (org-element-property :deadline hl))
               (tags (org-element-property :tags hl))
	       (timestamp (org-element-map (org-element-contents hl) 'timestamp
			    #'identity nil t))
               ;; Parent headline, search up the tree
               (parent (org-element-property :raw-value
                                             (org-element-property :parent hl)))
               ;; Classify as a task or event
               (kind (if (or todo scheduled deadline) "task" "event")))
          (when (or todo scheduled deadline timestamp)
            (push
	     (append
              `((title . ,title)
		(todo . ,todo)
		(tags . ,tags)
		(file . ,file)
		(parent . ,parent)
		(kind . ,kind))
	      ;; Each timestamp parsed into its own object, then flattened into the rest
	      (cal-server/org-parse-timestamp scheduled "scheduled")
	      (cal-server/org-parse-timestamp deadline "deadline")
	      (cal-server/org-parse-timestamp timestamp "timestamp"))
             results)))))
    ;; JSON encode and print to stdout
    (princ (json-encode (nreverse results)))))


(defun cal-server/org-extract-tasks ()
  "Extract tasks/events from current Org buffer and print JSON.
Iterate over headlines as the primary unit. Only include timestamps that
directly belong to the headline (not child headlines)."
  (let ((results '())
        (file (buffer-file-name)))
    (org-element-map (org-element-parse-buffer) 'headline
      (lambda (hl)
        (let* ((todo      (org-element-property :todo-keyword hl))
               (title     (org-element-property :raw-value hl))
               (scheduled (org-element-property :scheduled hl))
               (deadline  (org-element-property :deadline hl))
               ;; Gather only timestamps whose immediate parent is this headline
               (timestamps (org-element-map (org-element-contents hl) 'timestamp
                             (lambda (ts)
                               (when (eq (org-element-lineage ts '(headline) t) hl)
                                 ts))))
	       ;; (tags      (org-element-property :tags hl))
	       (tags (save-excursion
		       (goto-char (org-element-property :begin hl))
		       (org-get-tags)))
               (parent    (org-element-property :raw-value
						(org-element-property :parent hl)))
               (kind      (if (or todo scheduled deadline) "task" "event")))
          (when (or todo scheduled deadline timestamps)
            (if timestamps
		;; multiple timestamps = multiple entries
		(dolist (ts timestamps)
                  (push
                   (append
                    `((title . ,title)
                      (todo . ,todo)
                      (tags . ,tags)
                      (file . ,file)
                      (parent . ,parent)
                      (kind . ,kind))
                    (cal-server/org-parse-timestamp scheduled "scheduled")
                    (cal-server/org-parse-timestamp deadline "deadline")
                    (cal-server/org-parse-timestamp ts "timestamp"))
                   results))
              ;; no inline timestamps → still push one entry
              (push
               (append
		`((title . ,title)
                  (todo . ,todo)
                  (tags . ,tags)
                  (file . ,file)
                  (parent . ,parent)
                  (kind . ,kind))
		(cal-server/org-parse-timestamp scheduled "scheduled")
		(cal-server/org-parse-timestamp deadline "deadline"))
               results))))))
    (princ (json-encode (nreverse results)))))
