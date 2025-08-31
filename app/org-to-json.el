(require 'org)
(require 'org-element)
(require 'json)

(defun org-extract-tasks ()
  "Extract tasks/events from current Org buffer and print JSON."
  (let (results)
    (org-element-map (org-element-parse-buffer) 'headline
      (lambda (hl)
	(let* ((todo (org-element-property :todo-keyword hl))
	       (title (org-element-property :raw-value hl))
	       (scheduled (org-element-property :scheduled hl))
	       (deadline (org-element-property :deadline hl))
	       (timestamp (org-element-property :timestamp hl)))
	  (when (or todo scheduled deadline timestamp)
	    (push `((title . ,title)
		    (todo . ,todo)
		    (scheduled . ,(when scheduled
				    (org-element-property :raw-value scheduled)))
		    (deadline . ,(when deadline
				   (org-element-property :raw-value deadline)))
		    (timestamp . ,(when timestamp
				    (org-element-property :raw-value timestamp))))
		  results)))))
    ;; JSON encode and print to stdout
    (princ (json-encode (nreverse results)))))

;(when noninteractive
;  (find-file (car command-line-args-left))
;  (org-extract-tasks)
;  (kill-emacs 0))
	       
