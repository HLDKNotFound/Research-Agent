import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';
import { projectsApi } from '../api/projects';
import { useUI } from '../context/UIContext';

export const useProjects = () => {
  const queryClient = useQueryClient();
  const { activeProjectId, setActiveProjectId } = useUI();

  const projectsQuery = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
    staleTime: 5 * 60 * 1000, // 5 minutes cache
  });

  const projects = projectsQuery.data?.items || [];

  // Automatically select the first project if none is active
  useEffect(() => {
    if (!activeProjectId && projects.length > 0) {
      setActiveProjectId(projects[0].id);
    }
  }, [activeProjectId, projects, setActiveProjectId]);

  const createProjectMutation = useMutation({
    mutationFn: ({ name, description }: { name: string; description?: string }) =>
      projectsApi.create(name, description),
    onSuccess: (newProject) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      setActiveProjectId(newProject.id);
    },
  });

  const activeProject = projects.find((p) => p.id === activeProjectId);

  return {
    projects,
    activeProject,
    activeProjectId,
    setActiveProjectId,
    isLoading: projectsQuery.isLoading,
    isError: projectsQuery.isError,
    createProject: createProjectMutation.mutateAsync,
    isCreating: createProjectMutation.isPending,
  };
};
